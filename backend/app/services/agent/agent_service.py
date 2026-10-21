import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from google import genai
from google.genai import types

from backend.app.core.config import settings
from backend.app.services.workspace.workspace_manager import workspace_manager
from backend.app.services.tools.workspace_tools import (
    WORKSPACE_TOOLS,
    list_project_files,
    search_code,
    read_file,
    inspect_dependencies,
    discover_tests_and_commands,
    run_tests,
    edit_file,
    write_file,
    revert_file,
    get_workspace_diff
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

MODEL_COMPATIBILITY_MAP = {
    "gemini-2.5-flash": "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite": "gemini-3.5-flash-lite",
    "gemini-2.0-flash": "gemini-3.5-flash-lite",
    "gemini-1.5-flash": "gemini-3.5-flash-lite",
    "gemini-2.5-pro": "gemini-3.1-pro-preview",
}


class AgentOrchestrator:
    """
    Autonomous software investigation and code repair agent.
    Operates on real project source files within isolated workspaces using
    native Gemini function-calling.
    Enforces real test validation and safe workspace tool execution.
    Does NOT use synthetic or deterministic fallback simulations.
    """

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        self.max_iterations = settings.max_agent_iterations
        self.max_tool_calls = settings.max_tool_calls

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def run_project_investigation(
        self,
        investigation_id: str,
        project_id: str,
        issue_description: Optional[str] = None
    ) -> Tuple[InvestigationReportModel, List[InvestigationEventModel]]:
        """
        Main entry point for project investigation and repair.
        Explicitly requires a valid Gemini API key.
        """
        project = workspace_manager.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found in workspace.")

        if not settings.has_gemini_key:
            raise ValueError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env "
                "to execute live AI project investigations. Automatic simulation fallback has been disabled."
            )

        try:
            return self._run_gemini_project_loop(
                investigation_id=investigation_id,
                project_id=project_id,
                project=project,
                issue_description=issue_description
            )
        except Exception as e:
            logger.error(f"Gemini live agent execution failed: {e}", exc_info=True)
            raise RuntimeError(f"Live AI Agent investigation failed: {str(e)}")

    def _send_chat_message(
        self,
        chat: Any,
        content: Any,
        events: List[InvestigationEventModel],
        max_retries: int = 4
    ) -> Any:
        for attempt in range(max_retries):
            try:
                return chat.send_message(content)
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "rate limit" in err_str
                is_server_error = (
                    "500" in err_str or "internal" in err_str
                    or "502" in err_str or "bad gateway" in err_str
                    or "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                    or "504" in err_str or "timeout" in err_str
                )

                if (is_rate_limit or is_server_error) and attempt < max_retries - 1:
                    wait_sec = 5 * (attempt + 1) if is_server_error else 12 * (attempt + 1)
                    reason = "Free-tier rate limit (RPM) reached" if is_rate_limit else "Transient Google server error (500/503)"
                    msg = f"{reason}. Automatically pausing for {wait_sec}s before retrying (attempt {attempt + 1}/{max_retries})..."
                    logger.warning(msg)
                    events.append(
                        InvestigationEventModel(
                            event_id=f"evt-{len(events) + 1}",
                            timestamp=self._now(),
                            stage="Resilience Retry",
                            type="status",
                            message=msg,
                            is_gemini_native=True
                        )
                    )
                    time.sleep(wait_sec)
                else:
                    raise

    def _run_gemini_project_loop(
        self,
        investigation_id: str,
        project_id: str,
        project: Dict[str, Any],
        issue_description: Optional[str] = None
    ) -> Tuple[InvestigationReportModel, List[InvestigationEventModel]]:
        events: List[InvestigationEventModel] = []
        evidence_list: List[EvidenceModel] = []

        active_model = self.model_name
        if active_model in MODEL_COMPATIBILITY_MAP:
            mapped_model = MODEL_COMPATIBILITY_MAP[active_model]
            events.append(
                InvestigationEventModel(
                    event_id=f"evt-{len(events) + 1}",
                    timestamp=self._now(),
                    stage="Model Routing",
                    type="status",
                    message=f"Model '{active_model}' is deprecated for new keys; automatically routed to active compatible model '{mapped_model}'.",
                    is_gemini_native=True
                )
            )
            active_model = mapped_model

        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Agent Initialization",
                type="status",
                message=f"Gemini Agent initialized with model '{active_model}' for project '{project.get('name')}'.",
                is_gemini_native=True
            )
        )

        # Pre-gather baseline diagnostic status (tests and manifests)
        # This saves multiple API round trips, prevents exhausting RPM quotas, and gives the model instant context
        baseline_test = run_tests(project_id=project_id)
        initial_test_failure = None
        if not baseline_test.get("passed", True):
            initial_test_failure = baseline_test

        new_evidence = self._extract_workspace_evidence("run_tests", {"project_id": project_id}, baseline_test)
        evidence_list.extend(new_evidence)

        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Baseline Diagnosis",
                type="tool_result",
                message=f"Diagnostic tests: {'PASSED' if baseline_test.get('passed') else 'FAILED'}",
                tool_name="run_tests",
                tool_result=baseline_test,
                is_gemini_native=True
            )
        )

        client = genai.Client(api_key=self.api_key)

        tool_list = [
            list_project_files,
            search_code,
            read_file,
            inspect_dependencies,
            discover_tests_and_commands,
            run_tests,
            edit_file,
            write_file,
            revert_file,
            get_workspace_diff
        ]

        system_instruction = (
            "You are SentinelGraph, an expert autonomous AI software project investigation and repair agent.\n"
            "You are operating on a real software project inside an isolated workspace.\n"
            f"The target project_id is: '{project_id}'.\n\n"
            "YOUR INVESTIGATION & REPAIR PROTOCOL:\n"
            "1. Inspect the stack trace, failing file, and assertion provided in the diagnostic baseline.\n"
            "2. Read the failing source files with `read_file` or search with `search_code` to locate the defect.\n"
            "3. Apply a targeted fix using `edit_file` (or `write_file`) to resolve the root cause.\n"
            "4. Immediately re-run `run_tests` to verify that all tests now pass!\n"
            "5. Call `get_workspace_diff` to review your patch.\n"
            "6. Formulate a final summary explaining what broke, why it broke, and how your fix resolved it.\n"
            "Base all your reasoning on actual tool execution outputs."
        )

        chat = client.chats.create(
            model=active_model,
            config=types.GenerateContentConfig(
                tools=tool_list,
                system_instruction=system_instruction,
                temperature=0.1
            )
        )

        test_summary = baseline_test.get("output", "")
        if len(test_summary) > 2500:
            test_summary = test_summary[-2500:]

        initial_prompt = (
            f"Please investigate project '{project.get('name')}' (project_id: '{project_id}').\n"
            f"User Goal / Issue: {issue_description or 'Diagnose test failures, apply a verified code fix, and confirm resolution.'}\n\n"
            f"DIAGNOSTIC BASELINE:\n"
            f"- Status: {'PASSED' if baseline_test.get('passed') else 'FAILED'}\n"
            f"- Execution Output:\n```\n{test_summary}\n```\n\n"
            "Inspect this diagnostic output, read relevant files, apply the required fix using `edit_file`, and verify with `run_tests`."
        )

        events.append(
            InvestigationEventModel(
                event_id=f"evt-{len(events) + 1}",
                timestamp=self._now(),
                stage="Investigation Start",
                type="status",
                message=f"Dispatched project '{project.get('name')}' to Gemini Agent.",
                is_gemini_native=True
            )
        )

        response = self._send_chat_message(chat, initial_prompt, events)
        iterations = 0
        total_tool_calls = 0

        initial_test_failure = None

        while iterations < self.max_iterations and total_tool_calls < self.max_tool_calls:
            iterations += 1
            function_calls = getattr(response, "function_calls", None)

            if not function_calls:
                events.append(
                    InvestigationEventModel(
                        event_id=f"evt-{len(events) + 1}",
                        timestamp=self._now(),
                        stage="Synthesis",
                        type="conclusion",
                        message="Gemini completed investigation and repair actions.",
                        is_gemini_native=True
                    )
                )
                break

            tool_responses = []
            for call in function_calls:
                total_tool_calls += 1
                tool_name = call.name
                tool_args = dict(call.args) if call.args else {}

                # Guarantee project_id is passed
                tool_args["project_id"] = project_id

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

                if tool_name in WORKSPACE_TOOLS:
                    tool_func = WORKSPACE_TOOLS[tool_name]
                    try:
                        result = tool_func(**tool_args)
                    except Exception as ex:
                        result = {"status": "error", "error": f"Tool execution failed: {str(ex)}"}
                else:
                    result = {"status": "error", "error": f"Unknown workspace tool: '{tool_name}'"}

                # Capture initial test failure for report summary
                if tool_name == "run_tests" and not result.get("passed", True) and not initial_test_failure:
                    initial_test_failure = result

                # Extract verifiable evidence from tool result
                new_evidence = self._extract_workspace_evidence(tool_name, tool_args, result)
                evidence_list.extend(new_evidence)

                events.append(
                    InvestigationEventModel(
                        event_id=f"evt-{len(events) + 1}",
                        timestamp=self._now(),
                        stage="Observation & Action",
                        type="tool_result",
                        message=f"Executed {tool_name}: {result.get('message') or result.get('status')}",
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

            # Small pacing pause between tool iterations to stay smoothly under free tier RPM limits
            time.sleep(1.5)

            # Return tool execution outputs back to Gemini with safe retry
            response = self._send_chat_message(chat, tool_responses, events)

        # Final verification: execute real tests in the workspace to evaluate final state
        final_test_run = run_tests(project_id=project_id)
        diff_info = get_workspace_diff(project_id=project_id)
        gemini_reasoning = getattr(response, "text", None) if response else None

        report = self._construct_project_report(
            investigation_id=investigation_id,
            project_id=project_id,
            project=project,
            initial_test_failure=initial_test_failure,
            final_test_run=final_test_run,
            diff_info=diff_info,
            evidence_list=evidence_list,
            gemini_reasoning=gemini_reasoning
        )

        return report, events

    def _extract_workspace_evidence(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Dict[str, Any]
    ) -> List[EvidenceModel]:
        evidence = []
        now = self._now()

        if tool_name == "run_tests":
            status_str = "PASSED" if result.get("passed") else "FAILED"
            evidence.append(
                EvidenceModel(
                    id=f"EVID-TEST-{len(evidence) + 1}-{int(datetime.now().timestamp())}",
                    type="test_execution",
                    title=f"Test Suite Execution: {status_str} (Exit Code {result.get('exit_code')})",
                    description=result.get("output", "")[:400],
                    source="pytest_subprocess",
                    timestamp=now,
                    relevance="high",
                    observed=True,
                    metadata={
                        "command": result.get("command"),
                        "exit_code": result.get("exit_code"),
                        "passed": result.get("passed"),
                        "duration": result.get("duration_seconds")
                    }
                )
            )

        elif tool_name == "read_file" and result.get("status") == "success":
            evidence.append(
                EvidenceModel(
                    id=f"EVID-FILE-{tool_args.get('file_path')}",
                    type="code_inspection",
                    title=f"Source Code Inspection: {tool_args.get('file_path')}",
                    description=f"Read {result.get('total_lines')} lines from {tool_args.get('file_path')}.",
                    source="workspace_filesystem",
                    timestamp=now,
                    relevance="high",
                    observed=True,
                    metadata={"file": tool_args.get("file_path"), "lines": result.get("total_lines")}
                )
            )

        elif tool_name == "edit_file" and result.get("status") == "success":
            evidence.append(
                EvidenceModel(
                    id=f"EVID-PATCH-{tool_args.get('file_path')}",
                    type="code_patch",
                    title=f"Code Patch Applied: {tool_args.get('file_path')}",
                    description=result.get("message", "Target snippet replaced in source file."),
                    source="patch_engine",
                    timestamp=now,
                    relevance="high",
                    observed=True,
                    metadata={"file": tool_args.get("file_path")}
                )
            )

        elif tool_name == "search_code" and result.get("status") == "success":
            matches = result.get("matches", [])
            evidence.append(
                EvidenceModel(
                    id=f"EVID-SEARCH-{abs(hash(tool_args.get('query', '')))}",
                    type="code_search",
                    title=f"Search Code: '{tool_args.get('query')}' ({len(matches)} matches)",
                    description=f"Found {len(matches)} reference(s) across project codebase.",
                    source="code_indexer",
                    timestamp=now,
                    relevance="medium",
                    observed=True,
                    metadata={"query": tool_args.get("query"), "count": len(matches)}
                )
            )

        return evidence

    def _construct_project_report(
        self,
        investigation_id: str,
        project_id: str,
        project: Dict[str, Any],
        initial_test_failure: Optional[Dict[str, Any]],
        final_test_run: Dict[str, Any],
        diff_info: Dict[str, Any],
        evidence_list: List[EvidenceModel],
        gemini_reasoning: Optional[str] = None
    ) -> InvestigationReportModel:
        now = self._now()
        is_verified = final_test_run.get("passed", False)
        changed_files = diff_info.get("changed_files", [])
        patch_diff = diff_info.get("diff", "")

        observed_ids = [e.id for e in evidence_list]

        if is_verified:
            status = "completed"
            conf = 0.98
            conf_label = "High Confidence"
            rc_status = "probable"
            rc_title = "Defect Discovered and Automatically Remediated"
            rc_explanation = (
                f"Agent discovered a defect affecting project '{project.get('name')}'. "
                f"A targeted patch was applied to {', '.join(changed_files) if changed_files else 'source files'}. "
                f"Re-running tests confirmed full resolution with all tests passing (exit code 0)."
            )
            ver_status = "passed"
            ver_msg = (
                f"Real verification PASSED via test execution. "
                f"Exit Code: {final_test_run.get('exit_code')}, Duration: {final_test_run.get('duration_seconds')}s. "
                f"Tests passed: {final_test_run.get('tests_passed', 'All')}."
            )
        else:
            status = "unresolved"
            conf = 0.45
            conf_label = "Moderate Assessment"
            rc_status = "unconfirmed"
            rc_title = "Defect Investigation Inconclusive or Unresolved"
            rc_explanation = (
                "Tests continue to fail or defect could not be definitively resolved with the current patch."
            )
            ver_status = "failed"
            ver_msg = (
                f"Real verification FAILED. Test command exited with code {final_test_run.get('exit_code')}."
            )

        summary_text = (
            gemini_reasoning.strip() if gemini_reasoning and len(gemini_reasoning.strip()) > 30
            else (
                f"Autonomous investigation for project '{project.get('name')}'. "
                f"{'Defect successfully fixed and verified against real tests.' if is_verified else 'Test suite execution encountered failures.'}"
            )
        )

        failure_err = "Test failures detected"
        if initial_test_failure:
            failure_err = initial_test_failure.get("output", "")[:250]
        elif not is_verified:
            failure_err = final_test_run.get("output", "")[:250]

        return InvestigationReportModel(
            investigation_id=investigation_id,
            project_id=project_id,
            mode="AI AGENT MODE",
            status=status,
            summary=summary_text,
            failure=FailureSummaryModel(
                failure_id=f"FAIL-{project_id[:8].upper()}",
                title=f"Project Test Suite Failure ({project.get('name')})",
                description=failure_err,
                affected_component=changed_files[0] if changed_files else "project_source",
                timestamp=now,
                error_message=failure_err
            ),
            root_cause=RootCauseModel(
                title=rc_title,
                explanation=rc_explanation,
                confidence=conf,
                confidence_label=conf_label,
                status=rc_status,
                evidence_ids=observed_ids[:5]
            ),
            hypotheses=[
                HypothesisModel(
                    id="HYP-1",
                    title="Code Defect or Schema Incompatibility",
                    description="Source code mismatch or bug causing test failures.",
                    status="supported" if is_verified else "inconclusive",
                    supporting_evidence_ids=observed_ids[:3]
                )
            ],
            evidence=evidence_list,
            causal_chain=[
                "Discovered project test suite and entry points",
                "Executed baseline tests and captured error trace",
                "Inspected source files and identified root cause defect",
                f"Applied patch to {', '.join(changed_files) if changed_files else 'source code'}",
                f"Executed verification tests: {'PASS' if is_verified else 'FAIL'}"
            ],
            affected_components=changed_files if changed_files else ["src/"],
            recommendations=[
                RemediationOptionModel(
                    option_id="opt-apply-patch",
                    title="Apply Verified Code Patch",
                    target=", ".join(changed_files) if changed_files else "Source Code",
                    description="Apply the targeted code patch discovered and verified by SentinelGraph.",
                    trade_offs="Resolves failing tests directly in source code.",
                    resolves_failure=is_verified
                )
            ],
            remaining_unknowns=[] if is_verified else ["Unresolved test assertion errors in test suite"],
            verification=VerificationResultModel(
                status=ver_status,
                simulated=False,
                notice="REAL VERIFICATION VIA TEST EXECUTION",
                timestamp=now,
                applied_option_id="opt-apply-patch",
                applied_option_title="Apply Verified Code Patch",
                message=ver_msg,
                command=final_test_run.get("command"),
                exit_code=final_test_run.get("exit_code"),
                duration_seconds=final_test_run.get("duration_seconds"),
                tests_passed=final_test_run.get("tests_passed"),
                tests_failed=final_test_run.get("tests_failed"),
                output=final_test_run.get("output"),
                patch_diff=patch_diff
            ),
            diff=patch_diff,
            changed_files=changed_files
        )
