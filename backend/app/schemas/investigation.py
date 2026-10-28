from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class EvidenceModel(BaseModel):
    id: str
    type: str  # e.g., 'test_failure', 'code_inspection', 'dependency_contract', 'git_diff'
    title: str
    description: str
    source: str  # e.g., 'pytest_runner', 'code_search', 'api_contract'
    timestamp: str
    relevance: Literal["high", "medium", "low"] = "high"
    observed: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InvestigationEventModel(BaseModel):
    event_id: str
    timestamp: str
    stage: str
    type: Literal["status", "tool_call", "tool_result", "hypothesis", "conclusion", "error"]
    message: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    is_gemini_native: bool = False


class GraphNodePosition(BaseModel):
    x: float
    y: float


class GraphNodeData(BaseModel):
    label: str
    component_type: Literal["commit", "api_schema", "workflow_step", "failure", "external_service", "source_file", "test_file"]
    status: Literal["confirmed", "probable_cause", "affected_component", "unverified_hypothesis"]
    explanation: str
    evidence_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphNodeModel(BaseModel):
    id: str
    type: str = "customSentinel"
    position: GraphNodePosition
    data: GraphNodeData


class GraphEdgeModel(BaseModel):
    id: str
    source: str
    target: str
    label: str
    relationship: Literal[
        "modified",
        "provides",
        "consumes",
        "incompatible_with",
        "contributed_to",
        "observed_before",
        "tests",
        "imports",
        "repaired_by"
    ]
    animated: bool = False
    style: Optional[Dict[str, Any]] = None


class GraphDataModel(BaseModel):
    nodes: List[GraphNodeModel] = Field(default_factory=list)
    edges: List[GraphEdgeModel] = Field(default_factory=list)


class FailureSummaryModel(BaseModel):
    failure_id: str
    title: str
    description: str
    workflow_id: Optional[str] = None
    affected_component: str
    timestamp: str
    error_message: str


class RootCauseModel(BaseModel):
    title: str
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_label: Literal["High Confidence", "Moderate Assessment", "Unconfirmed / Insufficient Evidence"]
    status: Literal["probable", "unconfirmed"]
    evidence_ids: List[str] = Field(default_factory=list)


class HypothesisModel(BaseModel):
    id: str
    title: str
    description: str
    status: Literal["supported", "refuted", "inconclusive"]
    supporting_evidence_ids: List[str] = Field(default_factory=list)


class RemediationOptionModel(BaseModel):
    option_id: str
    title: str
    target: str
    description: str
    trade_offs: str
    resolves_failure: bool


class VerificationResultModel(BaseModel):
    status: Literal["passed", "failed", "not_run"]
    simulated: bool = False
    notice: str = "REAL VERIFICATION VIA TEST EXECUTION"
    timestamp: Optional[str] = None
    applied_option_id: Optional[str] = None
    applied_option_title: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None
    # Real test execution fields
    command: Optional[str] = None
    exit_code: Optional[int] = None
    duration_seconds: Optional[float] = None
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None
    output: Optional[str] = None
    patch_diff: Optional[str] = None


class InvestigationReportModel(BaseModel):
    investigation_id: str
    scenario_id: Optional[str] = None
    project_id: Optional[str] = None
    mode: str = "AI AGENT MODE"
    status: Literal["investigating", "completed", "unresolved", "failed"]
    summary: str
    failure: FailureSummaryModel
    root_cause: RootCauseModel
    hypotheses: List[HypothesisModel] = Field(default_factory=list)
    evidence: List[EvidenceModel] = Field(default_factory=list)
    causal_chain: List[str] = Field(default_factory=list)
    affected_components: List[str] = Field(default_factory=list)
    recommendations: List[RemediationOptionModel] = Field(default_factory=list)
    remaining_unknowns: List[str] = Field(default_factory=list)
    verification: VerificationResultModel
    diff: Optional[str] = None
    changed_files: List[str] = Field(default_factory=list)


class StartInvestigationRequest(BaseModel):
    scenario_id: Optional[str] = "scenario-invoice-field-rename"
    project_id: Optional[str] = None
    issue_description: Optional[str] = None
    force_deterministic: bool = False


class StartProjectInvestigationRequest(BaseModel):
    project_id: str
    issue_description: Optional[str] = None


class ApplyRemediationRequest(BaseModel):
    option_id: str


class ProjectUploadResponse(BaseModel):
    project_id: str
    name: str
    filename: str
    file_count: int
    total_size_bytes: int
    uncompressed_size_bytes: int
    created_at: str
    files: List[str]
    is_sample: bool = False
    stack: Optional[Dict[str, Any]] = None


class ProjectOverviewModel(BaseModel):
    project_id: str
    name: str
    filename: str
    file_count: int
    total_size_bytes: int
    created_at: str
    files: List[str] = Field(default_factory=list)
    is_sample: bool = False
    stack: Optional[Dict[str, Any]] = None


class WorkspaceDiffResponse(BaseModel):
    project_id: str
    changed_files: List[str]
    total_changed_files: int
    diff: str


class TestRunResultModel(BaseModel):
    status: str
    project_id: str
    command: Optional[str] = None
    exit_code: Optional[int] = None
    passed: bool
    duration_seconds: Optional[float] = None
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None
    output: Optional[str] = None
    message: str


class ScenarioOverviewModel(BaseModel):
    id: str
    name: str
    category: str
    description: str
    difficulty: str
    workflow_name: str
    error_message: str
    timestamp: str


class DashboardStatsModel(BaseModel):
    total_investigations: int
    resolved_investigations: int
    unresolved_investigations: int
    active_connections: int
    uploaded_projects: int = 0
    mode_available: str = "AI AGENT MODE"
    gemini_model_configured: str
    recent_investigations: List[Dict[str, Any]] = Field(default_factory=list)


class ConnectionStatusModel(BaseModel):
    id: str
    name: str
    type: str
    status: Literal["SIMULATED", "MOCK DATA", "NOT CONNECTED"]
    description: str
    last_sync: str
    records_available: int
