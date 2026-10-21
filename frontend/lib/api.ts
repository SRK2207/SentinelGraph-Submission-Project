import {
  HealthStatus,
  DashboardStats,
  ConnectionStatus,
  ScenarioOverview,
  InvestigationEvent,
  GraphData,
  InvestigationReport,
  VerificationResult,
  ProjectOverview,
  WorkspaceDiff,
  TestRunResult,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorMsg = errorJson.detail;
      }
    } catch {
      // fallback
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const api = {
  getHealth: () => request<HealthStatus>("/api/health"),
  getDashboard: () => request<DashboardStats>("/api/dashboard"),
  getConnections: () => request<ConnectionStatus[]>("/api/connections"),
  getScenarios: () => request<ScenarioOverview[]>("/api/scenarios"),

  // Project Workspace Endpoints
  uploadProject: async (file: File): Promise<ProjectOverview> => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/api/projects/upload`, {
      method: "POST",
      body: formData,
      cache: "no-store",
    });

    if (!res.ok) {
      let err = `Upload failed with status ${res.status}`;
      try {
        const j = await res.json();
        if (j.detail) err = j.detail;
      } catch {}
      throw new Error(err);
    }
    return res.json();
  },

  createSampleProject: () => request<ProjectOverview>("/api/projects/sample", { method: "POST" }),
  getProjects: () => request<ProjectOverview[]>("/api/projects"),
  getProject: (id: string) => request<ProjectOverview>(`/api/projects/${id}`),
  runProjectTests: (id: string) => request<TestRunResult>(`/api/projects/${id}/run-tests`, { method: "POST" }),
  getProjectDiff: (id: string) => request<WorkspaceDiff>(`/api/projects/${id}/diff`),
  resetProject: (id: string) => request<{ status: string; message: string }>(`/api/projects/${id}/reset`, { method: "POST" }),

  // Investigation & Repair Endpoints
  startInvestigation: (projectId: string, issueDescription?: string) =>
    request<{
      investigation_id: string;
      project_id: string;
      mode: string;
      status: string;
      message: string;
    }>("/api/investigations", {
      method: "POST",
      body: JSON.stringify({
        project_id: projectId,
        issue_description: issueDescription,
      }),
    }),

  getInvestigationEvents: (id: string) =>
    request<InvestigationEvent[]>(`/api/investigations/${id}/events`),
  getInvestigationGraph: (id: string) =>
    request<GraphData>(`/api/investigations/${id}/graph`),
  getInvestigationReport: (id: string) =>
    request<InvestigationReport>(`/api/investigations/${id}/report`),
  applyRemediation: (id: string, optionId: string) =>
    request<InvestigationReport>(`/api/investigations/${id}/remediation`, {
      method: "POST",
      body: JSON.stringify({ option_id: optionId }),
    }),
  verifyInvestigation: (id: string) =>
    request<VerificationResult>(`/api/investigations/${id}/verify`, {
      method: "POST",
    }),
  resetDemo: () =>
    request<{ status: string; message: string }>("/api/demo/reset", {
      method: "POST",
    }),
};
