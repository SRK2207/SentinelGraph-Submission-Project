"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { DashboardView } from "@/components/dashboard/DashboardView";
import { ConnectionsView } from "@/components/connections/ConnectionsView";
import { ScenarioSelectView } from "@/components/investigation/ScenarioSelectView";
import { LiveWorkspaceView } from "@/components/investigation/LiveWorkspaceView";
import { CausalGraphView } from "@/components/graph/CausalGraphView";
import { ReportView } from "@/components/reports/ReportView";
import { api } from "@/lib/api";
import {
  HealthStatus,
  DashboardStats,
  ConnectionStatus,
  ScenarioOverview,
  InvestigationReport,
  InvestigationEvent,
  GraphData,
} from "@/types";
import { AlertCircle, X } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);
  const [connections, setConnections] = useState<ConnectionStatus[]>([]);
  const [scenarios, setScenarios] = useState<ScenarioOverview[]>([]);

  // Active investigation state
  const [activeInvestigationId, setActiveInvestigationId] = useState<string | null>(null);
  const [activeReport, setActiveReport] = useState<InvestigationReport | null>(null);
  const [activeEvents, setActiveEvents] = useState<InvestigationEvent[]>([]);
  const [activeGraph, setActiveGraph] = useState<GraphData | null>(null);

  // Loading & status flags
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Initial load
  const loadInitialData = useCallback(async () => {
    try {
      const [h, d, c, s] = await Promise.all([
        api.getHealth(),
        api.getDashboard(),
        api.getConnections(),
        api.getScenarios(),
      ]);
      setHealth(h);
      setDashboardStats(d);
      setConnections(c);
      setScenarios(s);
    } catch (err: any) {
      console.warn("Backend not yet connected or initial load failed:", err);
      setErrorMessage(
        "Could not connect to FastAPI backend at http://localhost:8000. Ensure the backend server is running."
      );
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Load an existing investigation by ID
  const loadInvestigation = async (invId: string, targetTab: string = "workspace") => {
    try {
      setIsLoading(true);
      const [report, events, graph] = await Promise.all([
        api.getInvestigationReport(invId),
        api.getInvestigationEvents(invId),
        api.getInvestigationGraph(invId),
      ]);
      setActiveInvestigationId(invId);
      setActiveReport(report);
      setActiveEvents(events);
      setActiveGraph(graph);
      setActiveTab(targetTab);
      // Refresh stats
      const stats = await api.getDashboard();
      setDashboardStats(stats);
    } catch (err: any) {
      setErrorMessage(`Failed to load investigation ${invId}: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Launch a new investigation
  const handleLaunchInvestigation = async (
    scenarioId: string,
    forceDeterministic: boolean
  ) => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const launchRes = await api.startInvestigation(scenarioId, forceDeterministic);
      await loadInvestigation(launchRes.investigation_id, "workspace");
    } catch (err: any) {
      setErrorMessage(`Investigation launch failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Apply remediation option
  const handleApplyRemediation = async (optionId: string) => {
    if (!activeInvestigationId) return;
    try {
      const updatedReport = await api.applyRemediation(activeInvestigationId, optionId);
      setActiveReport(updatedReport);
    } catch (err: any) {
      setErrorMessage(`Failed to apply remediation: ${err.message}`);
    }
  };

  // Verify remediation
  const handleVerify = async () => {
    if (!activeInvestigationId) return;
    try {
      setIsVerifying(true);
      const verRes = await api.verifyInvestigation(activeInvestigationId);
      if (activeReport) {
        setActiveReport({
          ...activeReport,
          verification: verRes,
        });
      }
    } catch (err: any) {
      setErrorMessage(`Verification check failed: ${err.message}`);
    } finally {
      setIsVerifying(false);
    }
  };

  // Reset demonstration state
  const handleResetDemo = async () => {
    try {
      setIsResetting(true);
      await api.resetDemo();
      setActiveInvestigationId(null);
      setActiveReport(null);
      setActiveEvents([]);
      setActiveGraph(null);
      await loadInitialData();
      setActiveTab("dashboard");
    } catch (err: any) {
      setErrorMessage(`Failed to reset state: ${err.message}`);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-background text-slate-100">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        health={health}
        onResetDemo={handleResetDemo}
        isResetting={isResetting}
        hasActiveInvestigation={Boolean(activeReport)}
      />

      {/* Global Error Banner */}
      {errorMessage && (
        <div className="mx-auto mt-4 max-w-7xl px-4 sm:px-6 w-full">
          <div className="flex items-center justify-between rounded-lg bg-rose-950/80 p-3 text-xs text-rose-200 border border-rose-800">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 text-rose-400 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-rose-400 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 mx-auto w-full max-w-7xl p-4 sm:p-6 lg:p-8">
        {activeTab === "dashboard" && (
          <DashboardView
            stats={dashboardStats}
            onStartInvestigation={() => setActiveTab("investigate")}
            onSelectInvestigation={(id) => loadInvestigation(id, "workspace")}
            onNavigateToConnections={() => setActiveTab("connections")}
          />
        )}

        {activeTab === "investigate" && (
          <ScenarioSelectView
            scenarios={scenarios}
            health={health}
            onLaunchInvestigation={handleLaunchInvestigation}
            isLoading={isLoading}
          />
        )}

        {activeTab === "workspace" && (
          <LiveWorkspaceView
            report={activeReport}
            events={activeEvents}
            onNavigateToGraph={() => setActiveTab("graph")}
            onNavigateToReport={() => setActiveTab("report")}
          />
        )}

        {activeTab === "graph" && (
          <CausalGraphView
            graphData={activeGraph}
            evidenceList={activeReport?.evidence || []}
          />
        )}

        {activeTab === "report" && (
          <ReportView
            report={activeReport}
            onApplyRemediation={handleApplyRemediation}
            onVerify={handleVerify}
            isVerifying={isVerifying}
          />
        )}

        {activeTab === "connections" && (
          <ConnectionsView connections={connections} />
        )}
      </main>

      {/* Bottom Footer */}
      <footer className="border-t border-surface-border bg-surface/50 py-4 px-4 text-center text-[11px] text-slate-500">
        <div className="mx-auto max-w-7xl flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            SentinelGraph &copy; 2026 &middot; Autonomous Root-Cause Analysis
          </div>
          <div className="font-mono text-slate-400">
            Backend API: <span className="text-cyan-400">http://localhost:8000</span> &middot;
            Mode:{" "}
            <span className={health?.gemini_configured ? "text-emerald-400" : "text-amber-400"}>
              {health?.mode || "DETERMINISTIC DEMO MODE"}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
