"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { DashboardView } from "@/components/dashboard/DashboardView";
import { ConnectionsView } from "@/components/connections/ConnectionsView";
import { ProjectUploadView } from "@/components/investigation/ProjectUploadView";
import { LiveWorkspaceView } from "@/components/investigation/LiveWorkspaceView";
import { CausalGraphView } from "@/components/graph/CausalGraphView";
import { ReportView } from "@/components/reports/ReportView";
import { api } from "@/lib/api";
import {
  HealthStatus,
  DashboardStats,
  ConnectionStatus,
  InvestigationReport,
  InvestigationEvent,
  GraphData,
  ProjectOverview,
  TestRunResult,
} from "@/types";
import { AlertCircle, X, CheckCircle2 } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);
  const [connections, setConnections] = useState<ConnectionStatus[]>([]);
  const [projects, setProjects] = useState<ProjectOverview[]>([]);
  const [selectedProject, setSelectedProject] = useState<ProjectOverview | null>(null);

  // Active investigation state
  const [activeInvestigationId, setActiveInvestigationId] = useState<string | null>(null);
  const [activeReport, setActiveReport] = useState<InvestigationReport | null>(null);
  const [activeEvents, setActiveEvents] = useState<InvestigationEvent[]>([]);
  const [activeGraph, setActiveGraph] = useState<GraphData | null>(null);

  // Status flags
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load initial backend state and projects
  const loadInitialData = useCallback(async () => {
    try {
      const [h, d, c, pList] = await Promise.all([
        api.getHealth(),
        api.getDashboard(),
        api.getConnections(),
        api.getProjects(),
      ]);
      setHealth(h);
      setDashboardStats(d);
      setConnections(c);
      setProjects(pList);
      if (pList.length > 0 && !selectedProject) {
        setSelectedProject(pList[0]);
      }
    } catch (err: any) {
      console.warn("Backend not yet connected:", err);
      setErrorMessage(
        "Could not connect to FastAPI backend at http://localhost:8000. Ensure the backend server is running."
      );
    }
  }, [selectedProject]);

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

  // Upload Project ZIP
  const handleUploadZip = async (file: File) => {
    setErrorMessage(null);
    try {
      const uploaded = await api.uploadProject(file);
      setProjects((prev) => [uploaded, ...prev]);
      setSelectedProject(uploaded);
      setSuccessMessage(`Successfully extracted '${uploaded.name}' (${uploaded.file_count} files) into isolated workspace.`);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  // Load sample project
  const handleLoadSample = async () => {
    setErrorMessage(null);
    try {
      const sample = await api.createSampleProject();
      setProjects((prev) => {
        const filtered = prev.filter((p) => p.project_id !== sample.project_id);
        return [sample, ...filtered];
      });
      setSelectedProject(sample);
      setSuccessMessage("Loaded demo broken invoice service with test suite. Ready for autonomous repair.");
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  // Run baseline tests in workspace
  const handleRunTests = async (projectId: string): Promise<TestRunResult | null> => {
    try {
      return await api.runProjectTests(projectId);
    } catch (err: any) {
      setErrorMessage(`Failed to run tests: ${err.message}`);
      return null;
    }
  };

  // Launch AI investigation and repair
  const handleLaunchInvestigation = async (
    projectId: string,
    issueDescription?: string
  ) => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const launchRes = await api.startInvestigation(projectId, issueDescription);
      await loadInvestigation(launchRes.investigation_id, "workspace");
    } catch (err: any) {
      setErrorMessage(`Investigation failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Apply remediation
  const handleApplyRemediation = async (optionId: string) => {
    if (!activeInvestigationId) return;
    try {
      const updatedReport = await api.applyRemediation(activeInvestigationId, optionId);
      setActiveReport(updatedReport);
    } catch (err: any) {
      setErrorMessage(`Failed to apply remediation: ${err.message}`);
    }
  };

  // Verify remediation by executing tests
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

  // Reset workspace
  const handleResetWorkspace = async () => {
    try {
      setIsResetting(true);
      await api.resetDemo();
      setActiveInvestigationId(null);
      setActiveReport(null);
      setActiveEvents([]);
      setActiveGraph(null);
      await loadInitialData();
      setActiveTab("dashboard");
      setSuccessMessage("Workspace snapshots reset to original uploaded states.");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setErrorMessage(`Failed to reset workspace: ${err.message}`);
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
        onResetDemo={handleResetWorkspace}
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
            <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-white">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Global Success Banner */}
      {successMessage && (
        <div className="mx-auto mt-4 max-w-7xl px-4 sm:px-6 w-full">
          <div className="flex items-center justify-between rounded-lg bg-emerald-950/80 p-3 text-xs text-emerald-200 border border-emerald-800">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
              <span>{successMessage}</span>
            </div>
            <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-white">
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
          <ProjectUploadView
            health={health}
            projects={projects}
            selectedProject={selectedProject}
            onSelectProject={setSelectedProject}
            onUploadZip={handleUploadZip}
            onLoadSample={handleLoadSample}
            onLaunchInvestigation={handleLaunchInvestigation}
            onRunTests={handleRunTests}
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
            SentinelGraph &copy; 2026 &middot; Autonomous Software Project Investigation & Repair Agent
          </div>
          <div className="font-mono text-slate-400">
            Backend API: <span className="text-cyan-400">http://localhost:8000</span> &middot;
            Mode:{" "}
            <span className={health?.gemini_configured ? "text-emerald-400" : "text-amber-400"}>
              {health?.mode || "API KEY REQUIRED"}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
