from typing import Dict, Any, List, Optional
import uuid
import logging
from datetime import datetime, timezone

from backend.app.schemas.investigation import (
    InvestigationReportModel,
    InvestigationEventModel,
    GraphDataModel,
    VerificationResultModel,
    StartInvestigationRequest,
    ApplyRemediationRequest,
    DashboardStatsModel,
    ConnectionStatusModel,
    ScenarioOverviewModel,
    ProjectOverviewModel,
    FailureSummaryModel,
    RootCauseModel,
    RemediationOptionModel
)
from backend.app.core.config import settings
from backend.app.services.workspace.workspace_manager import workspace_manager
from backend.app.services.tools.workspace_tools import run_tests, get_workspace_diff
from backend.app.services.agent.agent_service import AgentOrchestrator
from backend.app.services.graph.graph_engine import CausalGraphEngine

logger = logging.getLogger("sentinelgraph.investigations")


class InvestigationRecord:
    def __init__(
        self,
        investigation_id: str,
        project_id: Optional[str],
        scenario_id: Optional[str],
        report: InvestigationReportModel,
        events: List[InvestigationEventModel],
        graph: GraphDataModel
    ):
        self.investigation_id = investigation_id
        self.project_id = project_id
        self.scenario_id = scenario_id
        self.report = report
        self.events = events
        self.graph = graph
        self.created_at = datetime.now(timezone.utc).isoformat()


class InvestigationManager:
    """
    Central manager for investigations, event histories, and real workspace states.
    Dispatches investigations to the live AI agent and verifies real test outcomes.
    """

    def __init__(self):
        self._investigations: Dict[str, InvestigationRecord] = {}
        self._agent = AgentOrchestrator()

    def get_dashboard_stats(self) -> DashboardStatsModel:
        total = len(self._investigations)
        resolved = sum(1 for inv in self._investigations.values() if inv.report.status == "completed")
        unresolved = sum(1 for inv in self._investigations.values() if inv.report.status == "unresolved")
        projects = workspace_manager.list_projects()

        recent = []
        for inv in reversed(list(self._investigations.values())):
            recent.append({
                "investigation_id": inv.investigation_id,
                "project_id": inv.project_id,
                "scenario_id": inv.scenario_id,
                "mode": inv.report.mode,
                "status": inv.report.status,
                "workflow": inv.report.failure.workflow_id or inv.project_id or "Test Suite",
                "timestamp": inv.created_at,
                "root_cause": inv.report.root_cause.title,
                "confidence_label": inv.report.root_cause.confidence_label
            })
            if len(recent) >= 5:
                break

        return DashboardStatsModel(
            total_investigations=total,
            resolved_investigations=resolved,
            unresolved_investigations=unresolved,
            active_connections=len(projects),
            uploaded_projects=len(projects),
            mode_available="AI AGENT MODE" if settings.has_gemini_key else "API KEY REQUIRED",
            gemini_model_configured=settings.gemini_model,
            recent_investigations=recent
        )

    def get_connections(self) -> List[ConnectionStatusModel]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        projects = workspace_manager.list_projects()
        connections = [
            ConnectionStatusModel(
                id="conn-gemini-ai",
                name="Google Gemini AI Engine",
                type="Agentic LLM Runtime",
                status="MOCK DATA" if not settings.has_gemini_key else "SIMULATED",
                description=f"Model: {settings.gemini_model}. {'Configured and ready.' if settings.has_gemini_key else 'API key not configured.'}",
                last_sync=now,
                records_available=1 if settings.has_gemini_key else 0
            ),
            ConnectionStatusModel(
                id="conn-workspace-fs",
                name="Isolated Project Workspaces",
                type="Filesystem Sandbox",
                status="MOCK DATA",
                description="Secure isolated filesystem sandboxes for uploaded project exploration and patching.",
                last_sync=now,
                records_available=len(projects)
            ),
            ConnectionStatusModel(
                id="conn-subprocess-runner",
                name="Subprocess Test Execution Runtime",
                type="Execution Sandbox",
                status="MOCK DATA",
                description="Sandboxed subprocess executor running pytest and test runners with strict timeouts.",
                last_sync=now,
                records_available=1
            )
        ]
        return connections

    def start_investigation(
        self,
        request: StartInvestigationRequest
    ) -> InvestigationRecord:
        investigation_id = f"INV-{uuid.uuid4().hex[:6].upper()}"

        # If project_id is provided, execute project investigation
        if request.project_id:
            project_id = request.project_id
            try:
                report, events = self._agent.run_project_investigation(
                    investigation_id=investigation_id,
                    project_id=project_id,
                    issue_description=request.issue_description
                )
            except ValueError:
                # Validation error (missing key, invalid project) raises ValueError for HTTP 400
                raise
            except Exception as e:
                logger.error(f"Investigation execution failed: {e}", exc_info=True)
                test_res = run_tests(project_id=project_id)
                diff_res = get_workspace_diff(project_id=project_id)
                err_msg = str(e)
                now_str = datetime.now(timezone.utc).isoformat()
                events = [
                    InvestigationEventModel(
                        event_id="evt-1",
                        timestamp=now_str,
                        stage="Diagnostic Check",
                        type="tool_result",
                        message=f"Baseline tests executed: {'PASSED' if test_res.get('passed') else 'FAILED'}",
                        tool_name="run_tests",
                        tool_result=test_res,
                        is_gemini_native=True
                    ),
                    InvestigationEventModel(
                        event_id="evt-2",
                        timestamp=now_str,
                        stage="AI Agent Execution",
                        type="error",
                        message=f"Agent encountered error: {err_msg}",
                        is_gemini_native=True
                    )
                ]
                report = InvestigationReportModel(
                    investigation_id=investigation_id,
                    project_id=project_id,
                    mode="AI AGENT MODE",
                    status="unresolved",
                    summary=f"Investigation could not fully complete automated repair: {err_msg}",
                    failure=FailureSummaryModel(
                        failure_id=f"fail-{investigation_id}",
                        title="Investigation Interrupted",
                        description=f"Automated repair was interrupted: {err_msg}",
                        workflow_id=project_id,
                        affected_component=project_id,
                        timestamp=now_str,
                        error_message=err_msg
                    ),
                    root_cause=RootCauseModel(
                        title="Investigation Incomplete",
                        explanation=f"Agent paused during execution: {err_msg}",
                        confidence=0.3,
                        confidence_label="Unconfirmed / Insufficient Evidence",
                        status="unconfirmed",
                        evidence_ids=[]
                    ),
                    hypotheses=[],
                    evidence=[],
                    causal_chain=[],
                    affected_components=[project_id],
                    recommendations=[
                        RemediationOptionModel(
                            option_id="opt-retry",
                            title="Retry Investigation",
                            target=project_id,
                            description="Retry autonomous investigation and repair with refreshed context.",
                            trade_offs="Consumes an additional AI reasoning turn.",
                            resolves_failure=False
                        )
                    ],
                    remaining_unknowns=["Automated synthesis did not complete."],
                    verification=VerificationResultModel(
                        status="passed" if test_res.get("passed") else "failed",
                        simulated=False,
                        notice="REAL VERIFICATION VIA TEST EXECUTION",
                        timestamp=now_str,
                        message=test_res.get("message", "Tests pending resolution."),
                        command=test_res.get("command"),
                        exit_code=test_res.get("exit_code"),
                        duration_seconds=test_res.get("duration_seconds"),
                        tests_passed=test_res.get("tests_passed"),
                        tests_failed=test_res.get("tests_failed"),
                        output=test_res.get("output"),
                        patch_diff=diff_res.get("diff")
                    ),
                    diff=diff_res.get("diff", ""),
                    changed_files=diff_res.get("changed_files", [])
                )

            # Build causal graph
            graph = CausalGraphEngine.build_graph_for_project(
                project_id=project_id,
                changed_files=report.changed_files,
                test_passed=(report.verification.status == "passed"),
                evidence_list=[e.model_dump() for e in report.evidence]
            )

            record = InvestigationRecord(
                investigation_id=investigation_id,
                project_id=project_id,
                scenario_id=None,
                report=report,
                events=events,
                graph=graph
            )
            self._investigations[investigation_id] = record
            return record

        else:
            # Fallback when no project specified: require a project
            projects = workspace_manager.list_projects()
            if projects:
                # Use the most recent project
                target_project_id = projects[0]["project_id"]
            else:
                # Create the built-in sample project
                sample_meta = workspace_manager.create_sample_broken_project()
                target_project_id = sample_meta["project_id"]

            return self.start_investigation(
                StartInvestigationRequest(
                    project_id=target_project_id,
                    issue_description=request.issue_description
                )
            )

    def get_investigation(self, investigation_id: str) -> Optional[InvestigationRecord]:
        return self._investigations.get(investigation_id)

    def get_events(self, investigation_id: str) -> Optional[List[InvestigationEventModel]]:
        record = self.get_investigation(investigation_id)
        if record:
            return record.events
        return None

    def get_graph(self, investigation_id: str) -> Optional[GraphDataModel]:
        record = self.get_investigation(investigation_id)
        if record:
            return record.graph
        return None

    def get_report(self, investigation_id: str) -> Optional[InvestigationReportModel]:
        record = self.get_investigation(investigation_id)
        if record:
            return record.report
        return None

    def apply_remediation(
        self,
        investigation_id: str,
        request: ApplyRemediationRequest
    ) -> Optional[InvestigationReportModel]:
        record = self.get_investigation(investigation_id)
        if not record:
            return None

        # Re-run real verification tests
        if record.project_id:
            test_res = run_tests(project_id=record.project_id)
            diff_res = get_workspace_diff(project_id=record.project_id)

            passed = test_res.get("passed", False)
            record.report.verification = VerificationResultModel(
                status="passed" if passed else "failed",
                simulated=False,
                notice="REAL VERIFICATION VIA TEST EXECUTION",
                timestamp=datetime.now(timezone.utc).isoformat(),
                applied_option_id=request.option_id,
                applied_option_title="Apply Verified Code Patch",
                message="Tests passed cleanly." if passed else "Tests failed upon execution.",
                command=test_res.get("command"),
                exit_code=test_res.get("exit_code"),
                duration_seconds=test_res.get("duration_seconds"),
                tests_passed=test_res.get("tests_passed"),
                tests_failed=test_res.get("tests_failed"),
                output=test_res.get("output"),
                patch_diff=diff_res.get("diff")
            )
            record.report.status = "completed" if passed else "unresolved"
            record.report.diff = diff_res.get("diff")
            record.report.changed_files = diff_res.get("changed_files", [])

        return record.report

    def verify_investigation(
        self,
        investigation_id: str
    ) -> Optional[VerificationResultModel]:
        record = self.get_investigation(investigation_id)
        if not record:
            return None

        if record.project_id:
            test_res = run_tests(project_id=record.project_id)
            diff_res = get_workspace_diff(project_id=record.project_id)
            passed = test_res.get("passed", False)

            res = VerificationResultModel(
                status="passed" if passed else "failed",
                simulated=False,
                notice="REAL VERIFICATION VIA TEST EXECUTION",
                timestamp=datetime.now(timezone.utc).isoformat(),
                applied_option_id=record.report.verification.applied_option_id or "opt-apply-patch",
                applied_option_title="Apply Verified Code Patch",
                message=f"Real test execution: {'PASS' if passed else 'FAIL'}. {test_res.get('message')}",
                command=test_res.get("command"),
                exit_code=test_res.get("exit_code"),
                duration_seconds=test_res.get("duration_seconds"),
                tests_passed=test_res.get("tests_passed"),
                tests_failed=test_res.get("tests_failed"),
                output=test_res.get("output"),
                patch_diff=diff_res.get("diff")
            )
            record.report.verification = res
            return res

        return None

    def reset_demo(self) -> Dict[str, Any]:
        self._investigations.clear()
        projects = workspace_manager.list_projects()
        for p in projects:
            workspace_manager.reset_project(p["project_id"])

        return {
            "status": "success",
            "message": "Project workspace reset to original state and investigation records cleared."
        }


# Global singleton manager instance
investigation_manager = InvestigationManager()
