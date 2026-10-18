from typing import Dict, Any, List, Optional
import uuid
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
    ScenarioOverviewModel
)
from backend.app.core.config import settings
from backend.app.data.scenarios import (
    get_all_scenarios,
    get_scenario,
    reset_all_scenarios
)
from backend.app.services.agent.agent_service import AgentOrchestrator
from backend.app.services.graph.graph_engine import CausalGraphEngine
from backend.app.services.verification.verifier import VerificationEngine


class InvestigationRecord:
    def __init__(
        self,
        investigation_id: str,
        scenario_id: str,
        report: InvestigationReportModel,
        events: List[InvestigationEventModel],
        graph: GraphDataModel
    ):
        self.investigation_id = investigation_id
        self.scenario_id = scenario_id
        self.report = report
        self.events = events
        self.graph = graph
        self.created_at = datetime.now(timezone.utc).isoformat()


class InvestigationManager:
    """
    Central manager for investigations, event histories, and graph models.
    Stores records in-memory for the local MVP.
    """

    def __init__(self):
        self._investigations: Dict[str, InvestigationRecord] = {}
        self._agent = AgentOrchestrator()

    def get_dashboard_stats(self) -> DashboardStatsModel:
        total = len(self._investigations)
        resolved = sum(1 for inv in self._investigations.values() if inv.report.status == "completed")
        unresolved = sum(1 for inv in self._investigations.values() if inv.report.status == "unresolved")

        recent = []
        for inv in reversed(list(self._investigations.values())):
            recent.append({
                "investigation_id": inv.investigation_id,
                "scenario_id": inv.scenario_id,
                "mode": inv.report.mode,
                "status": inv.report.status,
                "workflow": inv.report.failure.workflow_id,
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
            active_connections=4,
            mode_available="AI AGENT MODE" if settings.has_gemini_key else "DETERMINISTIC DEMO MODE",
            gemini_model_configured=settings.gemini_model,
            recent_investigations=recent
        )

    def get_connections(self) -> List[ConnectionStatusModel]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return [
            ConnectionStatusModel(
                id="conn-git-repo",
                name="Source Repository (Git)",
                type="Version Control System",
                status="MOCK DATA",
                description="Simulated Git repository index containing recent commits, authors, and schema diffs.",
                last_sync=now,
                records_available=3
            ),
            ConnectionStatusModel(
                id="conn-backend-api",
                name="Customer Profile API",
                type="Microservice / REST",
                status="SIMULATED",
                description="Simulated customer profile backend service providing user entities and contracts.",
                last_sync=now,
                records_available=1
            ),
            ConnectionStatusModel(
                id="conn-schema-catalog",
                name="Data Contract & Schema Catalog",
                type="Contract Registry",
                status="MOCK DATA",
                description="Simulated schema registry tracking field types, deprecations, and consumers.",
                last_sync=now,
                records_available=2
            ),
            ConnectionStatusModel(
                id="conn-workflow-engine",
                name="Invoice Dispatch Orchestrator",
                type="Workflow Automation",
                status="SIMULATED",
                description="Simulated automation engine executing multi-step business delivery workflows.",
                last_sync=now,
                records_available=2
            )
        ]

    def get_scenarios(self) -> List[ScenarioOverviewModel]:
        scenarios = get_all_scenarios()
        overview_list = []
        for s_id, s in scenarios.items():
            failure = s.get("failure", {})
            overview_list.append(
                ScenarioOverviewModel(
                    id=s_id,
                    name=s.get("name", s_id),
                    category=s.get("category", "General"),
                    description=s.get("description", ""),
                    difficulty=s.get("difficulty", "Standard"),
                    workflow_name=failure.get("workflow_name", "Unknown"),
                    error_message=failure.get("error_message", "Unknown error"),
                    timestamp=failure.get("timestamp", "")
                )
            )
        return overview_list

    def start_investigation(
        self,
        request: StartInvestigationRequest
    ) -> InvestigationRecord:
        scenario_id = request.scenario_id
        investigation_id = f"INV-{uuid.uuid4().hex[:6].upper()}"

        report, events = self._agent.run_investigation(
            investigation_id=investigation_id,
            scenario_id=scenario_id,
            force_deterministic=request.force_deterministic
        )

        # Build causal graph
        graph = CausalGraphEngine.build_graph_for_scenario(
            scenario_id=scenario_id,
            root_cause_status=report.root_cause.status,
            evidence_list=[e.model_dump() for e in report.evidence]
        )

        record = InvestigationRecord(
            investigation_id=investigation_id,
            scenario_id=scenario_id,
            report=report,
            events=events,
            graph=graph
        )

        self._investigations[investigation_id] = record
        return record

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

        # Verify chosen remediation option
        verification_result = VerificationEngine.verify_remediation(
            scenario_id=record.scenario_id,
            option_id=request.option_id
        )

        record.report.verification = verification_result
        return record.report

    def verify_investigation(
        self,
        investigation_id: str
    ) -> Optional[VerificationResultModel]:
        record = self.get_investigation(investigation_id)
        if not record:
            return None

        applied_opt = record.report.verification.applied_option_id
        if not applied_opt:
            # Default to first recommendation if none yet applied
            if record.report.recommendations:
                applied_opt = record.report.recommendations[0].option_id
            else:
                applied_opt = "opt-workflow-update"

        res = VerificationEngine.verify_remediation(
            scenario_id=record.scenario_id,
            option_id=applied_opt
        )
        record.report.verification = res
        return res

    def reset_demo(self) -> Dict[str, Any]:
        self._investigations.clear()
        reset_all_scenarios()
        return {
            "status": "success",
            "message": "Synthetic demonstration fixtures and investigation states successfully reset."
        }


# Global singleton manager instance
investigation_manager = InvestigationManager()
