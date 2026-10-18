import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from google import genai
from google.genai import types

from backend.app.core.config import settings
from backend.app.data.scenarios import get_scenario
from backend.app.services.tools.investigation_tools import (
    INVESTIGATION_TOOL_FUNCTIONS,
    get_failure_details,
    get_recent_commits,
    get_dependency_info,
    get_workflow_definition,
    inspect_commit,
)
from backend.app.schemas.investigation import (
    EvidenceModel,
    InvestigationEventModel,
    InvestigationReportModel,
    FailureSummaryModel,
    RootCauseModel,
    HypothesisModel,
    RemediationOptionModel,
    VerificationResultModel,
)

logger = logging.getLogger("sentinelgraph.agent")


class AgentOrchestrator:
    """
    Manages the investigative agent lifecycle.
    Orchestrates Gemini native function-calling with guardrails,
    records event timelines, extracts structured evidence, and provides
    a faithful deterministic fallback mode.
    """

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        self.max_iterations = settings.max_agent_iterations
        self.max_tool_calls = settings.max_tool_calls

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def run_investigation(
        self,
        investigation_id: str,
        scenario_id: str,
        force_deterministic: bool = False
    ) -> Tuple[InvestigationReportModel, List[InvestigationEventModel]]:
        scenario = get_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario '{scenario_id}' not found.")

        # Determine whether to run Gemini Agent Mode or Deterministic Demo Mode
        use_gemini = settings.has_gemini_key and not force_deterministic

        events: List[InvestigationEventModel] = []
        evidence_list: List[EvidenceModel] = []

        if use_gemini:
            try:
                report, events, evidence_list = self._run_gemini_agent_loop(
                    investigation_id=investigation_id,
                    scenario_id=scenario_id,
                    scenario=scenario
                )
                return report, events
            except Exception as e:
                logger.warning(
                    f"Gemini agent failed or rate-limited: {e}. Falling back to DETERMINISTIC DEMO MODE."
                )
                events.append(
                    InvestigationEventModel(
                        event_id=f"evt-{len(events) + 1}",
                        timestamp=self._now(),
                        stage="Fallback Initialization",
                        type="error",
                        message=f"Gemini API request failed ({type(e).__name__}). Automatically engaged DETERMINISTIC DEMO MODE.",
                        is_gemini_native=False
                    )
                )
                # Seamlessly fall back to deterministic mode with explicit label
                return self._run_deterministic_investigation(
                    investigation_id=investigation_id,
                    scenario_id=scenario_id,
                    scenario=scenario,
                    existing_events=events,
                    fallback_reason=str(e)
                )
        else:
            return self._run_deterministic_investigation(
                investigation_id=investigation_id,
                scenario_id=scenario_id,
                scenario=scenario,
                existing_events=[]
            )

    def _run_gemini_agent_loop(
        self,
        investigation_id: str,
        scenario_id: str,
        scenario: Dict[str, Any]
    ) -> Tuple[InvestigationReportModel, List[InvestigationEventModel], List[EvidenceModel]]:
        events: List[InvestigationEventModel] = []
        evidence_list: List[EvidenceModel] = []

        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Agent Initialization",
                type="status",
                message=f"Gemini Agent initialized with model '{self.model_name}'. Ready for dynamic tool selection.",
                is_gemini_native=True
            )
        )

        client = genai.Client(api_key=self.api_key)

        tool_list = [
            get_failure_details,
            get_recent_commits,
            get_dependency_info,
            get_workflow_definition,
            inspect_commit
        ]

        system_instruction = (
            "You are SentinelGraph, an expert agentic AI system for investigating cross-system workflow failures.\n"
            "Your goal is to investigate why a workflow failed by autonomously selecting appropriate tools.\n"
            "Always inspect failure details first, then check recent commits, workflow definition, dependencies, and commit diffs as needed.\n"
            "Evaluate competing hypotheses. Base all conclusions strictly on returned evidence.\n"
            "Do not fabricate root causes if the evidence is insufficient.\n"
            f"The target scenario_id to investigate is: '{scenario_id}'."
        )

        chat = client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                tools=tool_list,
                system_instruction=system_instruction,
                temperature=0.1
            )
        )

        initial_prompt = (
            f"An incident report has been triggered for scenario '{scenario_id}'. "
            "Please begin the investigation. Assess what information is missing, select the necessary tools, "
            "evaluate the returned evidence, and discover the probable root cause."
        )

        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Investigation Start",
                type="status",
                message="Submitted incident report to Gemini agent.",
                is_gemini_native=True
            )
        )

        response = chat.send_message(initial_prompt)
        iterations = 0
        total_tool_calls = 0

        while iterations < self.max_iterations and total_tool_calls < self.max_tool_calls:
            iterations += 1
            function_calls = response.function_calls

            if not function_calls:
                events.append(
                    InvestigationEventModel(
                        event_id=f"evt-{len(events) + 1}",
                        timestamp=self._now(),
                        stage="Synthesis",
                        type="conclusion",
                        message="Gemini completed investigation without requiring further tool executions.",
                        is_gemini_native=True
                    )
                )
                break

            tool_responses = []
            for call in function_calls:
                total_tool_calls += 1
                tool_name = call.name
                tool_args = dict(call.args) if call.args else {}

                # Guarantee scenario_id is supplied
                if "scenario_id" not in tool_args:
                    tool_args["scenario_id"] = scenario_id

                # Normalize argument aliases
                if tool_name == "inspect_commit" and "commit_id" not in tool_args:
                    for alias in ("commit_hash", "commit", "sha", "hash"):
                        if alias in tool_args:
                            tool_args["commit_id"] = tool_args[alias]
                            break
                elif tool_name == "get_recent_commits" and "limit" not in tool_args:
                    for alias in ("count", "n", "max_commits", "max_results"):
                        if alias in tool_args:
                            tool_args["limit"] = tool_args[alias]
                            break

                events.append(
                    InvestigationEventModel(
                        event_id=f"evt-{len(events) + 1}",
                        timestamp=self._now(),
                        stage="Dynamic Tool Selection",
                        type="tool_call",
                        message=f"Gemini selected tool: {tool_name}",
                        tool_name=tool_name,
                        tool_args=tool_args,
                        is_gemini_native=True
                    )
                )

                if tool_name in INVESTIGATION_TOOL_FUNCTIONS:
                    tool_func = INVESTIGATION_TOOL_FUNCTIONS[tool_name]
                    try:
                        result = tool_func(**tool_args)
                    except Exception as ex:
                        result = {"status": "error", "error": f"Tool execution failed: {str(ex)}"}
                else:
                    result = {"status": "error", "error": f"Unknown tool: '{tool_name}'"}

                # Extract verifiable evidence from tool result
                new_evidence = self._extract_evidence_from_result(tool_name, tool_args, result)
                evidence_list.extend(new_evidence)

                events.append(
                    InvestigationEventModel(
                        event_id=f"evt-{len(events) + 1}",
                        timestamp=self._now(),
                        stage="Observation & Evidence Collection",
                        type="tool_result",
                        message=f"Received result from {tool_name} ({len(new_evidence)} evidence item(s) captured)",
                        tool_name=tool_name,
                        tool_result=result,
                        is_gemini_native=True
                    )
                )

                tool_responses.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"result": result}
                    )
                )

            # Return tool execution outputs back to Gemini
            response = chat.send_message(tool_responses)

        # Capture Gemini natural language reasoning if produced
        gemini_reasoning = getattr(response, "text", None) if response else None

        # Build structured report strictly grounded in collected evidence
        report = self._construct_structured_report(
            investigation_id=investigation_id,
            scenario_id=scenario_id,
            scenario=scenario,
            mode="AI AGENT MODE",
            evidence_list=evidence_list,
            gemini_reasoning=gemini_reasoning
        )

        return report, events, evidence_list

    def _run_deterministic_investigation(
        self,
        investigation_id: str,
        scenario_id: str,
        scenario: Dict[str, Any],
        existing_events: Optional[List[InvestigationEventModel]] = None,
        fallback_reason: Optional[str] = None
    ) -> Tuple[InvestigationReportModel, List[InvestigationEventModel]]:
        events = existing_events if existing_events is not None else []
        evidence_list: List[EvidenceModel] = []

        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Investigation Start",
                type="status",
                message=f"Started controlled deterministic investigation trace for scenario '{scenario.get('name')}'.",
                is_gemini_native=False
            )
        )

        # Step 1: Failure Details
        tool_args_1 = {"scenario_id": scenario_id}
        res_1 = get_failure_details(**tool_args_1)
        ev_1 = self._extract_evidence_from_result("get_failure_details", tool_args_1, res_1)
        evidence_list.extend(ev_1)
        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Failure Inspection",
                type="tool_call",
                message="Retrieved failure details and exception trace.",
                tool_name="get_failure_details",
                tool_args=tool_args_1,
                tool_result=res_1,
                is_gemini_native=False
            )
        )

        # Step 2: Recent Commits
        tool_args_2 = {"scenario_id": scenario_id, "limit": 5}
        res_2 = get_recent_commits(**tool_args_2)
        ev_2 = self._extract_evidence_from_result("get_recent_commits", tool_args_2, res_2)
        evidence_list.extend(ev_2)
        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Commit History Analysis",
                type="tool_call",
                message=f"Retrieved {len(res_2.get('commits', []))} recent repository commits.",
                tool_name="get_recent_commits",
                tool_args=tool_args_2,
                tool_result=res_2,
                is_gemini_native=False
            )
        )

        # Step 3: Workflow Definition
        tool_args_3 = {"scenario_id": scenario_id}
        res_3 = get_workflow_definition(**tool_args_3)
        ev_3 = self._extract_evidence_from_result("get_workflow_definition", tool_args_3, res_3)
        evidence_list.extend(ev_3)
        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Workflow Contract Inspection",
                type="tool_call",
                message="Retrieved workflow step sequence and field requirements.",
                tool_name="get_workflow_definition",
                tool_args=tool_args_3,
                tool_result=res_3,
                is_gemini_native=False
            )
        )

        # Step 4: Dependencies
        tool_args_4 = {"scenario_id": scenario_id}
        res_4 = get_dependency_info(**tool_args_4)
        ev_4 = self._extract_evidence_from_result("get_dependency_info", tool_args_4, res_4)
        evidence_list.extend(ev_4)
        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Dependency Graph Discovery",
                type="tool_call",
                message="Analyzed cross-service upstream and downstream dependency contracts.",
                tool_name="get_dependency_info",
                tool_args=tool_args_4,
                tool_result=res_4,
                is_gemini_native=False
            )
        )

        # Step 5: Diff Inspection (if applicable)
        if scenario_id == "scenario-invoice-field-rename":
            tool_args_5 = {"scenario_id": scenario_id, "commit_id": "4f8a12d"}
            res_5 = inspect_commit(**tool_args_5)
            ev_5 = self._extract_evidence_from_result("inspect_commit", tool_args_5, res_5)
            evidence_list.extend(ev_5)
            events.append(
                InvestigationEventModel(
                    event_id=f"evt-{len(events) + 1}",
                    timestamp=self._now(),
                    stage="Commit Diff Analysis",
                    type="tool_call",
                    message="Inspected commit 4f8a12d: confirmed 'customer_email' was renamed to 'email'.",
                    tool_name="inspect_commit",
                    tool_args=tool_args_5,
                    tool_result=res_5,
                    is_gemini_native=False
                )
            )

        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Causal Chain Synthesis",
                type="conclusion",
                message="Completed investigation synthesis and generated evidence-backed causal report.",
                is_gemini_native=False
            )
        )

        report = self._construct_structured_report(
            investigation_id=investigation_id,
            scenario_id=scenario_id,
            scenario=scenario,
            mode="DETERMINISTIC DEMO MODE",
            evidence_list=evidence_list
        )

        return report, events

    def _extract_evidence_from_result(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Dict[str, Any]
    ) -> List[EvidenceModel]:
        evidence = []
        now = self._now()

        if tool_name == "get_failure_details" and result.get("status") == "success":
            evidence.append(
                EvidenceModel(
                    id=f"EVID-{result.get('failure_id', 'FAIL')}",
                    type="error_log",
                    title=f"Workflow Execution Failure: {result.get('error_type')}",
                    description=f"{result.get('error_message')} at execution {result.get('execution_id')}",
                    source="workflow_engine",
                    timestamp=result.get("timestamp", now),
                    relevance="high",
                    observed=True,
                    metadata={
                        "workflow_id": result.get("workflow_id"),
                        "component": result.get("affected_component")
                    }
                )
            )

        elif tool_name == "get_recent_commits" and result.get("status") == "success":
            for commit in result.get("commits", []):
                evidence.append(
                    EvidenceModel(
                        id=f"EVID-COMMIT-{commit.get('commit_id')}",
                        type="commit_metadata",
                        title=f"Commit {commit.get('commit_id')}: {commit.get('message')}",
                        description=f"Authored by {commit.get('author')}, modifying {len(commit.get('files_changed', []))} file(s).",
                        source="mock_repository",
                        timestamp=commit.get("timestamp", now),
                        relevance="high" if "api.py" in str(commit.get("files_changed")) else "medium",
                        observed=True,
                        metadata=commit
                    )
                )

        elif tool_name == "get_workflow_definition" and result.get("status") == "success":
            evidence.append(
                EvidenceModel(
                    id=f"EVID-WF-{result.get('workflow_id', 'DEF')}",
                    type="workflow_definition",
                    title=f"Workflow Definition: {result.get('name')}",
                    description=f"Consists of {len(result.get('steps', []))} steps. Requires fields defined in schema contract.",
                    source="orchestration_runtime",
                    timestamp=now,
                    relevance="high",
                    observed=True,
                    metadata={"steps": result.get("steps")}
                )
            )

        elif tool_name == "get_dependency_info" and result.get("status") == "success":
            for contract in result.get("field_contracts", []):
                evidence.append(
                    EvidenceModel(
                        id=f"EVID-CONTRACT-{contract.get('field_name')}",
                        type="dependency_contract",
                        title=f"Field Contract: {contract.get('field_name')}",
                        description=f"Produced by {contract.get('producer')} and consumed by {contract.get('consumer')}.",
                        source="api_catalog",
                        timestamp=now,
                        relevance="high",
                        observed=True,
                        metadata=contract
                    )
                )

        elif tool_name == "inspect_commit" and result.get("status") == "success":
            evidence.append(
                EvidenceModel(
                    id=f"EVID-DIFF-{result.get('commit_id')}",
                    type="commit_diff",
                    title=f"Commit Diff {result.get('commit_id')}: {result.get('file')}",
                    description=result.get("description", "Code diff inspected in repository history."),
                    source="git_diff_engine",
                    timestamp=now,
                    relevance="high",
                    observed=True,
                    metadata={
                        "file": result.get("file"),
                        "diff": result.get("diff")
                    }
                )
            )

        return evidence

    def _construct_structured_report(
        self,
        investigation_id: str,
        scenario_id: str,
        scenario: Dict[str, Any],
        mode: str,
        evidence_list: List[EvidenceModel],
        gemini_reasoning: Optional[str] = None
    ) -> InvestigationReportModel:
        failure_data = scenario.get("failure", {})
        remediation_raw = scenario.get("remediation_options", [])
        recs = [RemediationOptionModel(**r) for r in remediation_raw]
        observed_ids = {e.id for e in evidence_list}

        if scenario_id == "scenario-invoice-field-rename":
            has_diff = any("DIFF" in eid for eid in observed_ids)
            has_contract = any("CONTRACT" in eid for eid in observed_ids)
            has_fail = any("FAIL" in eid for eid in observed_ids)
            has_commit = any("COMMIT" in eid for eid in observed_ids)

            if has_diff:
                confidence = 0.96
                confidence_label = "High Confidence"
                rc_status = "probable"
                supported_ev_ids = [eid for eid in observed_ids if "DIFF-4f8a12d" in eid or "CONTRACT" in eid or "FAIL" in eid or "COMMIT-4f8a12d" in eid]
                explanation = (
                    "Commit 4f8a12d ('standardize response fields') in services/customer/api.py changed "
                    "the JSON response key from 'customer_email' to 'email'. The change was deployed "
                    "without updating dependent workflows, causing wf-invoice-gen-v2 step 3 to fail."
                )
                hyp1_status = "supported"
                hyp2_status = "refuted"
                investigation_status = "completed"
            elif has_commit or has_contract or has_fail:
                confidence = 0.65
                confidence_label = "Moderate Assessment"
                rc_status = "unconfirmed"
                supported_ev_ids = [eid for eid in observed_ids if "CONTRACT" in eid or "FAIL" in eid or "COMMIT" in eid]
                explanation = (
                    "Workflow failure indicates a missing 'customer_email' field, and recent commit history "
                    "shows modifications to services/customer/api.py. However, the exact code diff was not inspected "
                    "during this investigation, so the root cause remains an unconfirmed suspicion."
                )
                hyp1_status = "inconclusive"
                hyp2_status = "inconclusive"
                investigation_status = "completed"
            else:
                confidence = 0.20
                confidence_label = "Unconfirmed / Insufficient Evidence"
                rc_status = "unconfirmed"
                supported_ev_ids = []
                explanation = "No evidence was collected during the investigation. Root cause cannot be confirmed."
                hyp1_status = "inconclusive"
                hyp2_status = "inconclusive"
                investigation_status = "unresolved"

            summary_text = (
                gemini_reasoning.strip() if gemini_reasoning and len(gemini_reasoning.strip()) > 30
                else (
                    "Investigation confirmed a cross-system breaking contract change. "
                    "Commit 4f8a12d renamed the customer API response key 'customer_email' to 'email'. "
                    "The invoice automation workflow depends on 'customer_email' to extract the recipient, "
                    "causing a KeyError at step 3."
                )
            )

            return InvestigationReportModel(
                investigation_id=investigation_id,
                scenario_id=scenario_id,
                mode=mode,
                status=investigation_status,
                summary=summary_text,
                failure=FailureSummaryModel(
                    failure_id=failure_data.get("failure_id", "FAIL-9021"),
                    title="Invoice Customer Dispatcher Failure",
                    description=failure_data.get("error_message", "Field missing error"),
                    workflow_id=failure_data.get("workflow_id", "wf-invoice-gen-v2"),
                    affected_component=failure_data.get("affected_component", "invoice-generator"),
                    timestamp=failure_data.get("timestamp", self._now()),
                    error_message=failure_data.get("error_message", "")
                ),
                root_cause=RootCauseModel(
                    title="Backend API Field Rename Contract Break",
                    explanation=explanation,
                    confidence=confidence,
                    confidence_label=confidence_label,
                    status=rc_status,
                    evidence_ids=supported_ev_ids
                ),
                hypotheses=[
                    HypothesisModel(
                        id="HYP-1",
                        title="Backend API Field Renamed to 'email'",
                        description="Commit 4f8a12d renamed customer_email to email, breaking step 3 contract.",
                        status=hyp1_status,
                        supporting_evidence_ids=supported_ev_ids
                    ),
                    HypothesisModel(
                        id="HYP-2",
                        title="Redis Client Upgrade Incompatibility",
                        description="Commit 9c12b7e bumped Redis client version, potentially failing cache retrieval.",
                        status=hyp2_status,
                        supporting_evidence_ids=[]
                    )
                ],
                evidence=evidence_list,
                causal_chain=[
                    "Commit 4f8a12d refactored customer API",
                    "Customer API response key renamed: customer_email -> email",
                    "Invoice workflow step 3 expected customer_email",
                    "KeyError raised during invoice generation"
                ],
                affected_components=[
                    "services/customer/api.py",
                    "wf-invoice-gen-v2 (Invoice Customer Dispatcher)",
                    "billing-notification-worker"
                ],
                recommendations=recs,
                remaining_unknowns=[] if has_diff else ["Exact commit diff unobserved in investigation trace"],
                verification=VerificationResultModel(
                    status="not_run",
                    simulated=True,
                    message="Remediation not yet applied. Choose an option to simulate verification."
                )
            )

        else:
            # Ambiguous / insufficient evidence case
            supporting_ev_ids = [eid for eid in observed_ids if "FAIL" in eid]
            if not supporting_ev_ids and observed_ids:
                supporting_ev_ids = list(observed_ids)[:2]

            summary_text = (
                gemini_reasoning.strip() if gemini_reasoning and len(gemini_reasoning.strip()) > 30
                else (
                    "Investigation conducted across recent commits, repository diffs, and workflow definitions. "
                    "The upstream payment settlement gateway timed out after 30000ms. "
                    "None of the recent repository commits touched the payment gateway or timeout settings. "
                    "Available evidence is insufficient to confirm an internal root cause."
                )
            )

            return InvestigationReportModel(
                investigation_id=investigation_id,
                scenario_id=scenario_id,
                mode=mode,
                status="unresolved",
                summary=summary_text,
                failure=FailureSummaryModel(
                    failure_id=failure_data.get("failure_id", "FAIL-8842"),
                    title="Payment Reconciliation Timeout",
                    description=failure_data.get("error_message", "GatewayTimeoutError"),
                    workflow_id=failure_data.get("workflow_id", "wf-payment-reconcile"),
                    affected_component=failure_data.get("affected_component", "reconciliation-worker"),
                    timestamp=failure_data.get("timestamp", self._now()),
                    error_message=failure_data.get("error_message", "")
                ),
                root_cause=RootCauseModel(
                    title="Unconfirmed External Gateway Latency / Provider Downtime",
                    explanation=(
                        "Evidence shows an upstream gateway timeout (30s) occurred. "
                        "Recent repository commits (README updates, CSS styling) are unrelated. "
                        "Without external provider telemetry or network logs, root cause remains unconfirmed."
                    ),
                    confidence=0.35,
                    confidence_label="Unconfirmed / Insufficient Evidence",
                    status="unconfirmed",
                    evidence_ids=supporting_ev_ids
                ),
                hypotheses=[
                    HypothesisModel(
                        id="HYP-1",
                        title="Recent Repository Commits Introduced Regression",
                        description="Recent code changes in repo caused the timeout.",
                        status="refuted",
                        supporting_evidence_ids=[]
                    ),
                    HypothesisModel(
                        id="HYP-2",
                        title="Transient Upstream Provider Degradation",
                        description="External settlement partner experienced latency or transient downtime.",
                        status="inconclusive",
                        supporting_evidence_ids=supporting_ev_ids
                    )
                ],
                evidence=evidence_list,
                causal_chain=[
                    "Reconciliation worker initiated batch sync to partner gateway",
                    "HTTP timeout expired at 30000ms without response",
                    "GatewayTimeoutError raised",
                    "Recent commits checked and confirmed unrelated"
                ],
                affected_components=[
                    "wf-payment-reconcile",
                    "reconciliation-worker",
                    "https://settlement.partner.example.test"
                ],
                recommendations=recs,
                remaining_unknowns=[
                    "External settlement partner status & incident dashboard",
                    "Network egress packet drop rates between VPC and partner host"
                ],
                verification=VerificationResultModel(
                    status="not_run",
                    simulated=True,
                    message="Remediation not yet applied. Choose an option to simulate verification."
                )
            )
