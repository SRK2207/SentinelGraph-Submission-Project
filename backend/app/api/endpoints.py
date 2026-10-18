from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any

from backend.app.schemas.investigation import (
    DashboardStatsModel,
    ConnectionStatusModel,
    ScenarioOverviewModel,
    InvestigationReportModel,
    InvestigationEventModel,
    GraphDataModel,
    VerificationResultModel,
    StartInvestigationRequest,
    ApplyRemediationRequest,
)
from backend.app.services.investigations.investigation_manager import investigation_manager
from backend.app.core.config import settings

router = APIRouter()


@router.get("/health")
def get_health() -> Dict[str, Any]:
    """Health check returning backend status and safe configuration parameters."""
    return {
        "status": "healthy",
        "service": "SentinelGraph Backend",
        "version": "1.0.0",
        "mode": "AI AGENT MODE" if settings.has_gemini_key else "DETERMINISTIC DEMO MODE",
        "gemini_model": settings.gemini_model,
        "gemini_configured": settings.has_gemini_key
    }


@router.get("/dashboard", response_model=DashboardStatsModel)
def get_dashboard():
    """Retrieve dashboard statistics and recent investigations."""
    return investigation_manager.get_dashboard_stats()


@router.get("/connections", response_model=List[ConnectionStatusModel])
def get_connections():
    """Retrieve simulated integrations and mock connection states."""
    return investigation_manager.get_connections()


@router.get("/scenarios", response_model=List[ScenarioOverviewModel])
def get_scenarios():
    """Retrieve available demonstration scenarios."""
    return investigation_manager.get_scenarios()


@router.post("/investigations", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def start_investigation(request: StartInvestigationRequest):
    """Start an investigation using a selected scenario."""
    try:
        record = investigation_manager.start_investigation(request)
        return {
            "investigation_id": record.investigation_id,
            "scenario_id": record.scenario_id,
            "mode": record.report.mode,
            "status": record.report.status,
            "message": "Investigation completed successfully."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation failed to execute: {str(e)}"
        )


@router.get("/investigations/{investigation_id}", response_model=Dict[str, Any])
def get_investigation(investigation_id: str):
    """Retrieve overview details for an investigation."""
    record = investigation_manager.get_investigation(investigation_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")
    return {
        "investigation_id": record.investigation_id,
        "scenario_id": record.scenario_id,
        "mode": record.report.mode,
        "status": record.report.status,
        "created_at": record.created_at,
        "total_events": len(record.events),
        "total_evidence": len(record.report.evidence)
    }


@router.get("/investigations/{investigation_id}/events", response_model=List[InvestigationEventModel])
def get_investigation_events(investigation_id: str):
    """Retrieve investigation timeline events and tool execution trace."""
    events = investigation_manager.get_events(investigation_id)
    if events is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")
    return events


@router.get("/investigations/{investigation_id}/graph", response_model=GraphDataModel)
def get_investigation_graph(investigation_id: str):
    """Return the causal graph as structured React Flow nodes and edges."""
    graph = investigation_manager.get_graph(investigation_id)
    if graph is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")
    return graph


@router.get("/investigations/{investigation_id}/report", response_model=InvestigationReportModel)
def get_investigation_report(investigation_id: str):
    """Return the structured investigation report."""
    report = investigation_manager.get_report(investigation_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")
    return report


@router.post("/investigations/{investigation_id}/remediation", response_model=InvestigationReportModel)
def apply_remediation(investigation_id: str, request: ApplyRemediationRequest):
    """Record user's selected remediation and simulate verification."""
    report = investigation_manager.apply_remediation(investigation_id, request)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")
    return report


@router.post("/investigations/{investigation_id}/verify", response_model=VerificationResultModel)
def verify_investigation(investigation_id: str):
    """Run controlled simulated verification against synthetic fixture state."""
    res = investigation_manager.verify_investigation(investigation_id)
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")
    return res


@router.post("/demo/reset")
def reset_demo():
    """Reset synthetic demonstration state and cached investigations."""
    return investigation_manager.reset_demo()
