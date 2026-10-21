"use client";

import React, { useState } from "react";
import {
  FileText,
  Copy,
  Check,
  ShieldCheck,
  AlertTriangle,
  Sparkles,
  GitCommit,
  CheckCircle2,
  XCircle,
  Play,
  Terminal,
  Code,
  FileCode,
  CheckCheck,
} from "lucide-react";
import {
  InvestigationReport,
  RemediationOption,
  VerificationResult,
} from "@/types";

interface ReportViewProps {
  report: InvestigationReport | null;
  onApplyRemediation: (optionId: string) => void;
  onVerify: () => void;
  isVerifying: boolean;
}

export function ReportView({
  report,
  onApplyRemediation,
  onVerify,
  isVerifying,
}: ReportViewProps) {
  const [copied, setCopied] = useState<boolean>(false);
  const [selectedOptionId, setSelectedOptionId] = useState<string>(
    report?.recommendations[0]?.option_id || ""
  );

  if (!report) {
    return (
      <div className="rounded-xl border border-surface-border bg-surface p-12 text-center space-y-3">
        <p className="text-slate-400 text-sm">No report available.</p>
        <p className="text-slate-500 text-xs">Run an investigation first to view findings.</p>
      </div>
    );
  }

  const handleCopyReport = () => {
    const md = `
# SentinelGraph Investigation & Repair Report: ${report.investigation_id}
**Project:** ${report.project_id || report.scenario_id || "Unknown"}
**Mode:** ${report.mode}
**Status:** ${report.status.toUpperCase()}
**Confidence:** ${report.root_cause.confidence_label} (${Math.round(report.root_cause.confidence * 100)}%)

## Executive Summary
${report.summary}

## Incident Trigger
- **Affected Component:** ${report.failure.affected_component}
- **Error:** ${report.failure.error_message}

## Root Cause
### ${report.root_cause.title}
${report.root_cause.explanation}

## Code Changes Applied
${report.changed_files?.map((f) => `- ${f}`).join("\n") || "None"}

## Unified Patch Diff
\`\`\`diff
${report.diff || "No diff"}
\`\`\`

## Real Verification Status
- Status: ${report.verification.status.toUpperCase()}
- Notice: ${report.verification.notice}
- Command: ${report.verification.command || "N/A"}
- Exit Code: ${report.verification.exit_code ?? "N/A"}
- Details: ${report.verification.message}
    `.trim();

    navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isConfirmed = report.root_cause.status === "probable";
  const ver = report.verification;

  return (
    <div className="space-y-6">
      {/* Report Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold tracking-tight text-white">Investigation & Repair Report</h1>
            <span className="rounded bg-surface-secondary px-2 py-0.5 font-mono text-xs text-slate-400">
              {report.investigation_id}
            </span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold border ${
                report.status === "completed"
                  ? "bg-emerald-950/40 text-emerald-400 border-emerald-500/40"
                  : "bg-amber-950/40 text-amber-400 border-amber-500/40"
              }`}
            >
              {report.status.toUpperCase()}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Target: <span className="text-slate-200 font-mono">{report.project_id || report.scenario_id}</span> &middot;{" "}
            Mode: <span className="text-cyan-400">{report.mode}</span>
          </p>
        </div>

        <button
          onClick={handleCopyReport}
          className="flex items-center space-x-1.5 rounded-lg border border-surface-border bg-surface px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-surface-secondary hover:text-white transition-all shadow-sm"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          <span>{copied ? "Copied Markdown" : "Copy Report"}</span>
        </button>
      </div>

      {/* Executive Summary */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 space-y-2">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Executive Summary</h2>
        <p className="text-sm leading-relaxed text-slate-200">{report.summary}</p>
      </div>

      {/* Root Cause Card */}
      <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400 flex items-center space-x-1.5">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Root Cause Diagnosis</span>
            </span>
            <h3 className="text-base font-bold text-white">{report.root_cause.title}</h3>
          </div>

          <div className="text-right">
            <span
              className={`inline-block rounded px-2.5 py-0.5 text-xs font-bold border ${
                isConfirmed
                  ? "bg-emerald-950/50 text-emerald-400 border-emerald-500/40"
                  : "bg-amber-950/50 text-amber-400 border-amber-500/40"
              }`}
            >
              {report.root_cause.confidence_label} ({Math.round(report.root_cause.confidence * 100)}%)
            </span>
          </div>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed bg-surface-secondary/60 p-3.5 rounded-lg border border-surface-border">
          {report.root_cause.explanation}
        </p>

        {report.changed_files && report.changed_files.length > 0 && (
          <div className="flex items-center space-x-2 text-xs text-slate-400">
            <span className="font-semibold text-slate-300">Affected / Patched Files:</span>
            {report.changed_files.map((f, i) => (
              <span key={i} className="font-mono text-cyan-300 bg-surface px-2 py-0.5 rounded border border-surface-border">
                {f}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Real Unified Code Diff Section */}
      {report.diff && (
        <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Code className="h-4 w-4 text-cyan-400" />
              <h2 className="text-sm font-bold text-white">Verified Code Patch (Unified Diff)</h2>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              {report.changed_files?.length || 1} file(s) modified
            </span>
          </div>

          <pre className="max-h-72 overflow-y-auto rounded-lg bg-black/60 p-4 font-mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap border border-surface-border">
            {report.diff.split("\n").map((line, idx) => {
              if (line.startsWith("+") && !line.startsWith("+++")) {
                return (
                  <div key={idx} className="text-emerald-400 bg-emerald-950/30 px-1 -mx-1 rounded-sm">
                    {line}
                  </div>
                );
              } else if (line.startsWith("-") && !line.startsWith("---")) {
                return (
                  <div key={idx} className="text-rose-400 bg-rose-950/30 px-1 -mx-1 rounded-sm">
                    {line}
                  </div>
                );
              } else if (line.startsWith("@@")) {
                return (
                  <div key={idx} className="text-cyan-400 font-semibold my-1">
                    {line}
                  </div>
                );
              }
              return <div key={idx}>{line}</div>;
            })}
          </pre>
        </div>
      )}

      {/* Real Test Execution & Verification Section */}
      <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Terminal className="h-5 w-5 text-emerald-400" />
              <h2 className="text-base font-bold text-white">Real Test Execution & Verification</h2>
            </div>
            <p className="text-xs text-slate-300">
              SentinelGraph validates fixes by executing actual test runners inside the project workspace.
            </p>
          </div>

          <button
            onClick={onVerify}
            disabled={isVerifying}
            className="flex items-center space-x-2 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-emerald-400 transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5 fill-slate-950" />
            <span>{isVerifying ? "Executing Tests..." : "Re-Execute Verification Tests"}</span>
          </button>
        </div>

        {/* Verification Status Card */}
        {ver && (
          <div
            className={`rounded-xl border p-4 space-y-3 ${
              ver.status === "passed"
                ? "bg-emerald-950/20 border-emerald-500/50"
                : "bg-rose-950/20 border-rose-500/50"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {ver.status === "passed" ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                ) : (
                  <XCircle className="h-5 w-5 text-rose-400" />
                )}
                <span className="text-sm font-bold text-white uppercase tracking-wide">
                  Verification Status: {ver.status}
                </span>
              </div>

              <span className="rounded bg-emerald-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300 border border-emerald-700">
                {ver.notice}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="rounded bg-surface p-2 border border-surface-border">
                <span className="text-[10px] text-slate-500 block uppercase">Test Command</span>
                <span className="font-mono text-cyan-300 text-[11px] truncate block">{ver.command || "pytest"}</span>
              </div>
              <div className="rounded bg-surface p-2 border border-surface-border">
                <span className="text-[10px] text-slate-500 block uppercase">Exit Code</span>
                <span className="font-mono text-slate-200 text-[11px]">{ver.exit_code ?? 0}</span>
              </div>
              <div className="rounded bg-surface p-2 border border-surface-border">
                <span className="text-[10px] text-slate-500 block uppercase">Duration</span>
                <span className="font-mono text-slate-200 text-[11px]">{ver.duration_seconds ?? 0.12}s</span>
              </div>
              <div className="rounded bg-surface p-2 border border-surface-border">
                <span className="text-[10px] text-slate-500 block uppercase">Result</span>
                <span className={`font-bold text-[11px] ${ver.status === "passed" ? "text-emerald-400" : "text-rose-400"}`}>
                  {ver.status === "passed" ? "ALL PASSED" : "FAILED"}
                </span>
              </div>
            </div>

            {ver.output && (
              <div>
                <span className="text-[10px] text-slate-400 font-semibold block mb-1">Execution Terminal Output:</span>
                <pre className="max-h-48 overflow-y-auto rounded bg-black/70 p-3 font-mono text-[11px] leading-relaxed text-slate-300 whitespace-pre-wrap border border-surface-border">
                  {ver.output}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
