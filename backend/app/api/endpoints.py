from fastapi import APIRouter, HTTPException, UploadFile, File, status
from typing import List, Dict, Any, Optional

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
    ProjectUploadResponse,
    ProjectOverviewModel,
    WorkspaceDiffResponse,
    TestRunResultModel
)
from backend.app.services.investigations.investigation_manager import investigation_manager
from backend.app.services.workspace.workspace_manager import workspace_manager, WorkspaceSecurityError
from backend.app.services.tools.workspace_tools import run_tests
from backend.app.core.config import settings

router = APIRouter()


@router.get("/health")
def get_health() -> Dict[str, Any]:
    """Health check returning backend status, security isolation profile, and safe configuration parameters."""
    from backend.app.services.security.execution_sandbox import get_host_security_profile
    return {
        "status": "healthy",
        "service": "SentinelGraph AI Investigation & Repair Backend",
        "version": "2.0.0",
        "mode": "AI AGENT MODE" if settings.has_gemini_key else "API KEY REQUIRED",
        "gemini_model": settings.gemini_model,
        "gemini_configured": settings.has_gemini_key,
        "execution_security": get_host_security_profile().model_dump()
    }


@router.get("/dashboard", response_model=DashboardStatsModel)
def get_dashboard():
    """Retrieve dashboard statistics and recent investigations."""
    return investigation_manager.get_dashboard_stats()


@router.get("/connections", response_model=List[ConnectionStatusModel])
def get_connections():
    """Retrieve active system connections and workspace sandboxes."""
    return investigation_manager.get_connections()


# ============================================================
# PROJECT WORKSPACE ENDPOINTS (STEP 1 & STEP 2)
# ============================================================

@router.post("/projects/upload", response_model=ProjectUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_project(file: UploadFile = File(...)):
    """
    Upload a project ZIP archive.
    Safely validates, extracts into an isolated workspace, and protects against path traversal.
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only .zip archives are supported for project upload."
        )

    try:
        content = await file.read()
        metadata = workspace_manager.create_project_from_zip(content, file.filename)
        from backend.app.services.security.execution_sandbox import get_host_security_profile
        metadata["execution_security"] = get_host_security_profile().model_dump()
        return metadata
    except WorkspaceSecurityError as sec_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security rejection during extraction: {str(sec_err)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract project: {str(e)}"
        )


@router.post("/projects/sample", response_model=ProjectUploadResponse, status_code=status.HTTP_201_CREATED)
def create_sample_project():
    """
    Instantiate the built-in sample defective project with real tests for quick evaluation.
    """
    try:
        metadata = workspace_manager.create_sample_broken_project()
        from backend.app.services.security.execution_sandbox import get_host_security_profile
        metadata["execution_security"] = get_host_security_profile().model_dump()
        return metadata
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sample project: {str(e)}"
        )


@router.get("/projects", response_model=List[ProjectOverviewModel])
def list_projects():
    """Retrieve all uploaded project workspaces."""
    return workspace_manager.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectOverviewModel)
def get_project(project_id: str):
    """Retrieve project metadata for a specific workspace."""
    proj = workspace_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")
    return proj


@router.post("/projects/{project_id}/run-tests", response_model=TestRunResultModel)
def execute_project_tests(project_id: str, test_command: Optional[str] = None):
    """
    Execute tests inside the isolated workspace using real test runners.
    Returns actual output, return code, and pass/fail summary.
    """
    proj = workspace_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    res = run_tests(project_id=project_id, test_command=test_command)
    return res


@router.get("/projects/{project_id}/diff", response_model=WorkspaceDiffResponse)
def get_project_diff(project_id: str):
    """
    Retrieve unified diff comparing current workspace files against original uploaded snapshot.
    """
    proj = workspace_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    return workspace_manager.get_workspace_diff(project_id)


@router.post("/projects/{project_id}/reset")
def reset_project(project_id: str):
    """
    Reset project workspace files back to original uploaded snapshot.
    """
    try:
        return workspace_manager.reset_project(project_id)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================
# INVESTIGATION & REPAIR ENDPOINTS (STEP 3 & STEP 4)
# ============================================================

@router.post("/investigations", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def start_investigation(request: StartInvestigationRequest):
    """
    Start an autonomous AI investigation and repair process on an uploaded project.
    Requires GEMINI_API_KEY. Does not use fake or simulated fallback.
    """
    try:
        record = investigation_manager.start_investigation(request)
        return {
            "investigation_id": record.investigation_id,
            "project_id": record.project_id,
            "scenario_id": record.scenario_id,
            "mode": record.report.mode,
            "status": record.report.status,
            "message": "Investigation and repair completed successfully."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
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
        "project_id": record.project_id,
        "scenario_id": record.scenario_id,
        "mode": record.report.mode,
        "status": record.report.status,
        "created_at": record.created_at,
        "total_events": len(record.events),
        "total_evidence": len(record.report.evidence),
        "verified": record.report.verification.status == "passed"
    }


@router.get("/investigations/{investigation_id}/events", response_model=List[InvestigationEventModel])
def get_investigation_events(investigation_id: str):
    """Retrieve investigation timeline events and real tool execution trace."""
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
    """Return the structured investigation and repair report with real diff and verification."""
    report = investigation_manager.get_report(investigation_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")
    return report


@router.post("/investigations/{investigation_id}/remediation", response_model=InvestigationReportModel)
def apply_remediation(investigation_id: str, request: ApplyRemediationRequest):
    """Re-evaluate tests and record applied remediation."""
    report = investigation_manager.apply_remediation(investigation_id, request)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")
    return report


@router.post("/investigations/{investigation_id}/verify", response_model=VerificationResultModel)
def verify_investigation(investigation_id: str):
    """Run real test execution in the workspace to verify defect resolution."""
    res = investigation_manager.verify_investigation(investigation_id)
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")
    return res


@router.post("/demo/reset")
def reset_demo():
    """Reset workspaces and investigation records."""
    return investigation_manager.reset_demo()
