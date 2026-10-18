import {
  HealthStatus,
  DashboardStats,
  ConnectionStatus,
  ScenarioOverview,
  InvestigationEvent,
  GraphData,
  InvestigationReport,
  VerificationResult,
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
  startInvestigation: (scenarioId: string, forceDeterministic: boolean = false) =>
    request<{
      investigation_id: string;
      scenario_id: string;
      mode: "AI AGENT MODE" | "DETERMINISTIC DEMO MODE";
      status: string;
      message: string;
    }>("/api/investigations", {
      method: "POST",
      body: JSON.stringify({
        scenario_id: scenarioId,
        force_deterministic: forceDeterministic,
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
