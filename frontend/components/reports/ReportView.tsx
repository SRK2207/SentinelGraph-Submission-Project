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
  Workflow,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Play,
  RotateCcw,
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
# SentinelGraph Investigation Report: ${report.investigation_id}
**Scenario:** ${report.scenario_id}
**Mode:** ${report.mode}
**Status:** ${report.status.toUpperCase()}
**Confidence:** ${report.root_cause.confidence_label} (${Math.round(report.root_cause.confidence * 100)}%)

## Executive Summary
${report.summary}

## Incident Trigger
- **Workflow:** ${report.failure.workflow_id}
- **Component:** ${report.failure.affected_component}
- **Error:** ${report.failure.error_message}

## Probable Root Cause
### ${report.root_cause.title}
${report.root_cause.explanation}

## Causal Chain
${report.causal_chain.map((c, i) => `${i + 1}. ${c}`).join("\n")}

## Supporting Evidence
${report.evidence.map((e) => `- [${e.id}] (${e.source}): ${e.title} - ${e.description}`).join("\n")}

## Recommended Remediation
${report.recommendations.map((r) => `### ${r.title}\n${r.description}\n*Trade-offs:* ${r.trade_offs}`).join("\n\n")}

## Verification Status
- Status: ${report.verification.status.toUpperCase()}
- Notice: ${report.verification.notice}
- Details: ${report.verification.message}
    `.trim();

    navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleApply = (optId: string) => {
    setSelectedOptionId(optId);
    onApplyRemediation(optId);
  };

  const isConfirmed = report.root_cause.status === "probable";
  const ver = report.verification;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Bar with Copy Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-surface-border bg-surface p-5">
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-mono text-xs font-bold text-cyan-400">
              {report.investigation_id}
            </span>
            <span className="rounded bg-surface-secondary px-2 py-0.5 text-[10px] font-semibold text-slate-300 border border-surface-border">
              {report.mode}
            </span>
            <span
              className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                report.status === "completed"
                  ? "bg-emerald-950/40 text-emerald-400 border-emerald-500/30"
                  : "bg-amber-950/40 text-amber-400 border-amber-500/30"
              }`}
            >
              {report.status.toUpperCase()}
            </span>
          </div>
          <h1 className="text-lg font-bold text-white mt-1">Autonomous Root-Cause Report</h1>
        </div>

        <button
          onClick={handleCopyReport}
          className="inline-flex items-center space-x-1.5 rounded-lg border border-surface-border bg-surface-secondary px-3.5 py-2 text-xs font-semibold text-slate-200 hover:text-white hover:bg-surface-border transition-all"
        >
          {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
          <span>{copied ? "Copied to Clipboard!" : "Copy Report (Markdown)"}</span>
        </button>
      </div>

      {/* Executive Summary Card */}
      <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-3">
        <h2 className="text-xs font-mono uppercase tracking-wider text-slate-400">
          Executive Summary
        </h2>
        <p className="text-sm text-slate-200 leading-relaxed">{report.summary}</p>
      </div>

      {/* Root Cause Assessment Card */}
      <div
        className={`rounded-xl border p-6 space-y-4 ${
          isConfirmed
            ? "border-amber-500/50 bg-gradient-to-br from-surface to-amber-950/20"
            : "border-slate-700 bg-surface"
        }`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
                Primary Root-Cause Assessment
              </span>
              <span
                className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                  isConfirmed
                    ? "bg-amber-950/60 text-amber-400 border-amber-500/40"
                    : "bg-slate-800 text-slate-400 border-slate-600"
                }`}
              >
                {report.root_cause.confidence_label} ({Math.round(report.root_cause.confidence * 100)}%)
              </span>
            </div>
            <h3 className="text-lg font-bold text-white">{report.root_cause.title}</h3>
          </div>
        </div>

        <p className="text-xs text-slate-200 leading-relaxed">
          {report.root_cause.explanation}
        </p>

        {/* Linked Evidence Pills */}
        <div className="space-y-1.5 pt-2 border-t border-surface-border">
          <span className="text-[11px] font-semibold text-slate-400 block">
            Supporting Evidence References:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {report.root_cause.evidence_ids.map((id) => (
              <span
                key={id}
                className="font-mono text-xs rounded bg-surface-secondary px-2 py-0.5 text-cyan-400 border border-surface-border font-semibold"
              >
                {id}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Causal Chain Sequence */}
      <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-4">
        <h2 className="text-sm font-bold text-white flex items-center space-x-2">
          <Workflow className="h-4 w-4 text-cyan-400" />
          <span>Evidence-Backed Causal Chain</span>
        </h2>

        <div className="space-y-2">
          {report.causal_chain.map((step, idx) => (
            <div
              key={idx}
              className="flex items-center space-x-3 rounded-lg bg-surface-secondary/40 p-3 border border-surface-border text-xs"
            >
              <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-cyan-500/20 text-cyan-400 font-mono font-bold text-xs">
                {idx + 1}
              </div>
              <span className="text-slate-200 font-medium">{step}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Remaining Unknowns (If ambiguous) */}
      {report.remaining_unknowns && report.remaining_unknowns.length > 0 && (
        <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-5 space-y-3">
          <div className="flex items-center space-x-2 text-amber-400">
            <AlertTriangle className="h-4 w-4" />
            <h3 className="text-sm font-bold">Remaining Unknowns & Insufficient Evidence</h3>
          </div>
          <p className="text-xs text-slate-300">
            SentinelGraph identified that internal code commits do not explain this failure.
            The following external factors require out-of-band verification:
          </p>
          <ul className="list-disc list-inside space-y-1 text-xs text-amber-200/90 pl-1">
            {report.remaining_unknowns.map((unk, idx) => (
              <li key={idx}>{unk}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Interactive Remediation Section */}
      <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-5">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
            <h2 className="text-base font-bold text-white">Interactive Remediation Options</h2>
          </div>
          <p className="text-xs text-slate-300">
            Select a proposed remediation to apply to the simulated scenario state and verify the
            outcome.
          </p>
        </div>

        {/* Options List */}
        <div className="space-y-3">
          {report.recommendations.map((opt) => {
            const isSelected = (selectedOptionId || report.recommendations[0]?.option_id) === opt.option_id;

            return (
              <div
                key={opt.option_id}
                onClick={() => handleApply(opt.option_id)}
                className={`cursor-pointer rounded-xl border p-4 transition-all space-y-2 ${
                  isSelected
                    ? "bg-surface-secondary border-cyan-400 ring-1 ring-cyan-400/40"
                    : "bg-surface border-surface-border hover:border-surface-highlight"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-sm text-white">{opt.title}</span>
                    <span className="font-mono text-[10px] text-cyan-400 bg-surface px-1.5 py-0.5 rounded border border-surface-border">
                      {opt.target}
                    </span>
                  </div>

                  <span
                    className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                      opt.resolves_failure
                        ? "bg-emerald-950/60 text-emerald-400 border-emerald-500/40"
                        : "bg-rose-950/60 text-rose-400 border-rose-500/40"
                    }`}
                  >
                    {opt.resolves_failure ? "RESOLVES CAUSE" : "INEFFECTIVE"}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-normal">{opt.description}</p>

                <div className="text-[11px] text-slate-400 bg-background/60 p-2 rounded border border-surface-border">
                  <span className="font-semibold text-slate-300">Architectural Trade-offs: </span>
                  {opt.trade_offs}
                </div>
              </div>
            );
          })}
        </div>

        {/* Verification Action & Result Panel */}
        <div className="pt-2 border-t border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300">
              Run Automated Verification Check:
            </span>
            <button
              onClick={onVerify}
              disabled={isVerifying}
              className="flex items-center space-x-2 rounded-lg bg-emerald-500 px-5 py-2 text-xs font-bold text-slate-950 hover:bg-emerald-400 transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5 fill-slate-950" />
              <span>{isVerifying ? "Running Verification..." : "Run Simulated Verification"}</span>
            </button>
          </div>

          {/* Verification Status Card */}
          {ver && ver.status !== "not_run" && (
            <div
              className={`rounded-xl border p-4 space-y-2 ${
                ver.status === "passed"
                  ? "bg-emerald-950/30 border-emerald-500/50"
                  : "bg-rose-950/30 border-rose-500/50"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {ver.status === "passed" ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <XCircle className="h-4 w-4 text-rose-400" />
                  )}
                  <span className="text-xs font-bold text-white uppercase">
                    Verification Outcome: {ver.status}
                  </span>
                </div>

                <span className="text-[10px] font-mono font-bold text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/40">
                  {ver.notice}
                </span>
              </div>

              <p className="text-xs text-slate-200 leading-relaxed">{ver.message}</p>

              {ver.details && (
                <div className="mt-2 rounded bg-background/80 p-2.5 font-mono text-[10px] text-slate-300 border border-surface-border">
                  <pre className="whitespace-pre-wrap">
                    {JSON.stringify(ver.details, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
