export type InvestigationStatus = "queued" | "investigating" | "completed" | "unresolved" | "failed";

export type ComponentType = "commit" | "api_schema" | "workflow_step" | "failure" | "external_service" | "source_file" | "test_file";

export type NodeStatus = "confirmed" | "probable_cause" | "affected_component" | "unverified_hypothesis";

export type EdgeRelationship =
  | "modified"
  | "provides"
  | "consumes"
  | "incompatible_with"
  | "contributed_to"
  | "observed_before"
  | "tests"
  | "imports"
  | "repaired_by";

export interface Evidence {
  id: string;
  type: string;
  title: string;
  description: string;
  source: string;
  timestamp: string;
  relevance: "high" | "medium" | "low";
  observed: boolean;
  metadata: Record<string, any>;
}

export interface InvestigationEvent {
  event_id: string;
  timestamp: string;
  stage: string;
  type: "status" | "tool_call" | "tool_result" | "hypothesis" | "conclusion" | "error";
  message: string;
  tool_name?: string | null;
  tool_args?: Record<string, any> | null;
  tool_result?: Record<string, any> | null;
  is_gemini_native: boolean;
}

export interface GraphNodeData {
  [key: string]: any;
  label: string;
  component_type: ComponentType;
  status: NodeStatus;
  explanation: string;
  evidence_ids: string[];
  metadata: Record<string, any>;
}

export interface GraphNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: GraphNodeData;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  relationship: EdgeRelationship;
  animated: boolean;
  style?: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface FailureSummary {
  failure_id: string;
  title: string;
  description: string;
  workflow_id?: string | null;
  affected_component: string;
  timestamp: string;
  error_message: string;
}

export interface RootCause {
  title: string;
  explanation: string;
  confidence: number;
  confidence_label: "High Confidence" | "Moderate Assessment" | "Unconfirmed / Insufficient Evidence";
  status: "probable" | "unconfirmed";
  evidence_ids: string[];
}

export interface Hypothesis {
  id: string;
  title: string;
  description: string;
  status: "supported" | "refuted" | "inconclusive";
  supporting_evidence_ids: string[];
}

export interface RemediationOption {
  option_id: string;
  title: string;
  target: string;
  description: string;
  trade_offs: string;
  resolves_failure: boolean;
}

export interface VerificationResult {
  status: "passed" | "failed" | "not_run";
  simulated: boolean;
  notice: string;
  timestamp?: string | null;
  applied_option_id?: string | null;
  applied_option_title?: string | null;
  message: string;
  details?: Record<string, any> | null;
  command?: string | null;
  exit_code?: number | null;
  duration_seconds?: number | null;
  tests_passed?: number | null;
  tests_failed?: number | null;
  output?: string | null;
  patch_diff?: string | null;
}

export interface InvestigationReport {
  investigation_id: string;
  scenario_id?: string | null;
  project_id?: string | null;
  mode: string;
  status: InvestigationStatus;
  summary: string;
  failure: FailureSummary;
  root_cause: RootCause;
  hypotheses: Hypothesis[];
  evidence: Evidence[];
  causal_chain: string[];
  affected_components: string[];
  recommendations: RemediationOption[];
  remaining_unknowns: string[];
  verification: VerificationResult;
  diff?: string | null;
  changed_files?: string[];
}

export interface ProjectOverview {
  project_id: string;
  name: string;
  filename: string;
  file_count: number;
  total_size_bytes: number;
  created_at: string;
  files: string[];
  is_sample?: boolean;
}

export interface WorkspaceDiff {
  project_id: string;
  changed_files: string[];
  total_changed_files: number;
  diff: string;
}

export interface TestRunResult {
  status: string;
  project_id: string;
  command?: string | null;
  exit_code?: number | null;
  passed: boolean;
  duration_seconds?: number | null;
  tests_passed?: number | null;
  tests_failed?: number | null;
  output?: string | null;
  message: string;
}

export interface ScenarioOverview {
  id: string;
  name: string;
  category: string;
  description: string;
  difficulty: string;
  workflow_name: string;
  error_message: string;
  timestamp: string;
}

export interface DashboardStats {
  total_investigations: number;
  resolved_investigations: number;
  unresolved_investigations: number;
  active_connections: number;
  uploaded_projects?: number;
  mode_available: string;
  gemini_model_configured: string;
  recent_investigations: Array<{
    investigation_id: string;
    project_id?: string;
    scenario_id?: string;
    mode: string;
    status: string;
    workflow: string;
    timestamp: string;
    root_cause: string;
    confidence_label: string;
  }>;
}

export interface ConnectionStatus {
  id: string;
  name: string;
  type: string;
  status: "SIMULATED" | "MOCK DATA" | "NOT CONNECTED";
  description: string;
  last_sync: string;
  records_available: number;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  mode: string;
  gemini_model: string;
  gemini_configured: boolean;
}
