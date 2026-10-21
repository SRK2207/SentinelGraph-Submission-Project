"use client";

import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileCode,
  Folder,
  Play,
  RotateCcw,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Terminal,
  ShieldCheck,
  Layers,
  ArrowRight,
} from "lucide-react";
import { ProjectOverview, HealthStatus, TestRunResult } from "@/types";

interface ProjectUploadViewProps {
  health: HealthStatus | null;
  projects: ProjectOverview[];
  selectedProject: ProjectOverview | null;
  onSelectProject: (proj: ProjectOverview) => void;
  onUploadZip: (file: File) => Promise<void>;
  onLoadSample: () => Promise<void>;
  onLaunchInvestigation: (projectId: string, issueDescription?: string) => Promise<void>;
  onRunTests: (projectId: string) => Promise<TestRunResult | null>;
  isLoading: boolean;
}

export function ProjectUploadView({
  health,
  projects,
  selectedProject,
  onSelectProject,
  onUploadZip,
  onLoadSample,
  onLaunchInvestigation,
  onRunTests,
  isLoading,
}: ProjectUploadViewProps) {
  const [dragOver, setDragOver] = useState(false);
  const [issueDescription, setIssueDescription] = useState("");
  const [uploading, setUploading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestRunResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith(".zip")) {
        setUploading(true);
        try {
          await onUploadZip(file);
        } finally {
          setUploading(false);
        }
      } else {
        alert("Please upload a .zip archive of your project repository.");
      }
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setUploading(true);
      try {
        await onUploadZip(file);
      } finally {
        setUploading(false);
      }
    }
  };

  const handleRunBaselineTests = async () => {
    if (!selectedProject) return;
    setTesting(true);
    try {
      const res = await onRunTests(selectedProject.project_id);
      setTestResult(res);
    } finally {
      setTesting(false);
    }
  };

  const isGeminiReady = health?.gemini_configured ?? false;

  return (
    <div className="space-y-6">
      {/* Top Banner Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-surface-border pb-5">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center space-x-2">
            <span>Autonomous Software Project Investigation & Repair</span>
            <span className="rounded-full bg-cyan-950/60 px-2.5 py-0.5 text-xs font-semibold text-cyan-400 border border-cyan-800/60">
              Isolated Workspace
            </span>
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Upload your software project archive. SentinelGraph autonomously discovers test suites, explores source code,
            diagnoses failures, applies targeted code patches, and verifies fixes with real test execution.
          </p>
        </div>

        {/* Quick Sample Button */}
        <div className="flex items-center space-x-3 flex-shrink-0">
          <button
            onClick={onLoadSample}
            disabled={isLoading || uploading}
            className="flex items-center space-x-2 rounded-lg border border-cyan-500/40 bg-cyan-950/30 px-3.5 py-2 text-xs font-medium text-cyan-300 hover:bg-cyan-900/40 hover:text-white transition-all shadow-sm disabled:opacity-50"
            title="Load built-in invoice microservice with known defect for demonstration"
          >
            <Sparkles className="h-4 w-4 text-cyan-400" />
            <span>Load Demo Broken Project</span>
          </button>
        </div>
      </div>

      {/* Missing Gemini API Key Warning */}
      {!isGeminiReady && (
        <div className="rounded-xl border border-amber-600/60 bg-amber-950/30 p-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-amber-200">
              <span className="font-semibold text-amber-300">GEMINI API KEY REQUIRED FOR LIVE AGENT: </span>
              SentinelGraph executes genuine Gemini dynamic tool calls without simulated fallbacks.
              Please add <code className="rounded bg-black/40 px-1 py-0.5 font-mono text-amber-300">GEMINI_API_KEY=your_key</code> to{" "}
              <code className="rounded bg-black/40 px-1 py-0.5 font-mono text-amber-300">backend/.env</code> and restart the backend.
            </div>
          </div>
        </div>
      )}

      {/* Main Grid: Upload & Project Selection */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Upload Zone & Project Library */}
        <div className="lg:col-span-5 space-y-6">
          {/* Drag & Drop Upload Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-all ${
              dragOver
                ? "border-cyan-400 bg-cyan-950/20"
                : "border-surface-border bg-surface hover:border-slate-500 hover:bg-surface-secondary/70"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-cyan-500/10 text-cyan-400 mb-3">
              <UploadCloud className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-white">
              {uploading ? "Extracting Workspace..." : "Upload Project ZIP Archive"}
            </h3>
            <p className="mt-1 text-xs text-slate-400">
              Drag & drop a <span className="font-mono text-slate-300">.zip</span> archive here, or click to browse.
            </p>
            <div className="mt-3 flex items-center justify-center space-x-2 text-[11px] text-slate-500">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              <span>Path-traversal safe &middot; Isolated sandbox</span>
            </div>
          </div>

          {/* Uploaded Projects List */}
          <div className="rounded-xl border border-surface-border bg-surface p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                <Layers className="h-3.5 w-3.5 text-cyan-400" />
                <span>Uploaded Workspaces ({projects.length})</span>
              </span>
            </div>

            {projects.length === 0 ? (
              <div className="py-6 text-center text-xs text-slate-500">
                No projects uploaded yet. Drop a .zip archive above or click "Load Demo Broken Project".
              </div>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {projects.map((proj) => {
                  const isSelected = selectedProject?.project_id === proj.project_id;
                  return (
                    <div
                      key={proj.project_id}
                      onClick={() => {
                        onSelectProject(proj);
                        setTestResult(null);
                      }}
                      className={`cursor-pointer rounded-lg border p-3 transition-all ${
                        isSelected
                          ? "border-cyan-500/70 bg-cyan-950/30 text-white shadow-sm"
                          : "border-surface-border bg-surface-secondary/40 text-slate-300 hover:border-slate-600 hover:bg-surface-secondary"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2 truncate">
                          <Folder className={`h-4 w-4 flex-shrink-0 ${isSelected ? "text-cyan-400" : "text-slate-400"}`} />
                          <span className="text-xs font-semibold truncate">{proj.name}</span>
                        </div>
                        {proj.is_sample && (
                          <span className="rounded bg-indigo-950/80 px-1.5 py-0.5 text-[10px] font-medium text-indigo-300 border border-indigo-800">
                            Sample
                          </span>
                        )}
                      </div>
                      <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                        <span>{proj.file_count} files</span>
                        <span className="font-mono text-[10px]">{Math.round(proj.total_size_bytes / 1024)} KB</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Selected Project Inspection & Launch Action */}
        <div className="lg:col-span-7 space-y-6">
          {selectedProject ? (
            <div className="rounded-xl border border-surface-border bg-surface p-5 space-y-5">
              {/* Project Header */}
              <div className="flex items-start justify-between border-b border-surface-border pb-4">
                <div>
                  <div className="flex items-center space-x-2">
                    <h2 className="text-base font-bold text-white">{selectedProject.name}</h2>
                    <span className="rounded bg-surface-secondary px-2 py-0.5 font-mono text-[11px] text-slate-400">
                      {selectedProject.project_id}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    Source archive: <span className="font-mono text-slate-300">{selectedProject.filename}</span> &middot;{" "}
                    {selectedProject.file_count} files extracted safely.
                  </p>
                </div>

                {/* Run Baseline Tests Button */}
                <button
                  onClick={handleRunBaselineTests}
                  disabled={testing}
                  className="flex items-center space-x-1.5 rounded-lg border border-slate-700 bg-surface-secondary px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-surface-border hover:text-white transition-all disabled:opacity-50"
                  title="Run tests in workspace right now"
                >
                  <Terminal className={`h-3.5 w-3.5 ${testing ? "animate-spin text-cyan-400" : "text-slate-400"}`} />
                  <span>{testing ? "Running..." : "Run Tests"}</span>
                </button>
              </div>

              {/* Baseline Test Execution Result Banner */}
              {testResult && (
                <div
                  className={`rounded-lg border p-3.5 text-xs ${
                    testResult.passed
                      ? "border-emerald-600/60 bg-emerald-950/30 text-emerald-200"
                      : "border-rose-600/60 bg-rose-950/30 text-rose-200"
                  }`}
                >
                  <div className="flex items-center justify-between font-semibold">
                    <span className="flex items-center space-x-2">
                      {testResult.passed ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-rose-400" />
                      )}
                      <span>
                        Baseline Test Result: {testResult.passed ? "ALL TESTS PASS" : "FAILURES DETECTED"} (Exit code:{" "}
                        {testResult.exit_code})
                      </span>
                    </span>
                    <span className="font-mono text-[10px] opacity-75">{testResult.duration_seconds}s</span>
                  </div>
                  <pre className="mt-2.5 max-h-36 overflow-y-auto rounded bg-black/50 p-2.5 font-mono text-[11px] leading-relaxed text-slate-300 whitespace-pre-wrap">
                    {testResult.output}
                  </pre>
                </div>
              )}

              {/* File Tree Preview */}
              <div>
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-2">
                  Project Files Extracted
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto rounded-lg border border-surface-border bg-surface-secondary/50 p-3">
                  {selectedProject.files.map((f, idx) => (
                    <div key={idx} className="flex items-center space-x-2 text-xs text-slate-300 truncate">
                      <FileCode className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0" />
                      <span className="font-mono text-[11px] truncate">{f}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Issue Description / Prompt Input */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                  <span>Investigation Goal or Failure Description (Optional)</span>
                  <span className="text-[11px] font-normal text-slate-500">Leave blank for full auto-discovery</span>
                </label>
                <textarea
                  value={issueDescription}
                  onChange={(e) => setIssueDescription(e.target.value)}
                  placeholder="e.g., Run test suite, inspect failing KeyError on customer profile response, apply verified patch to resolve."
                  rows={2}
                  className="w-full rounded-lg border border-surface-border bg-surface-secondary px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              {/* Launch Autonomous Investigation Button */}
              <div className="pt-2">
                <button
                  onClick={() => onLaunchInvestigation(selectedProject.project_id, issueDescription)}
                  disabled={isLoading || !isGeminiReady}
                  className={`w-full flex items-center justify-center space-x-2 rounded-xl py-3 text-sm font-semibold transition-all shadow-lg ${
                    isGeminiReady
                      ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 hover:from-cyan-400 hover:to-blue-500 shadow-cyan-500/20"
                      : "cursor-not-allowed bg-slate-800 text-slate-500"
                  }`}
                >
                  <Sparkles className="h-4 w-4" />
                  <span>
                    {isLoading
                      ? "Autonomous AI Agent Investigating & Repairing..."
                      : "Start Autonomous AI Investigation & Repair"}
                  </span>
                  <ArrowRight className="h-4 w-4 ml-1" />
                </button>
                <p className="mt-2 text-center text-[11px] text-slate-500">
                  The AI agent will explore workspace files, execute tests, apply a code patch, and verify the fix.
                </p>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-surface-border bg-surface p-12 text-center">
              <Folder className="mx-auto h-12 w-12 text-slate-600 mb-3" />
              <h3 className="text-sm font-semibold text-white">No Project Selected</h3>
              <p className="mt-1 text-xs text-slate-400 max-w-sm mx-auto">
                Select an uploaded workspace from the left or click "Load Demo Broken Project" to inspect and repair.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
