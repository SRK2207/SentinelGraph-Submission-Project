"use client";

import React, { useState } from "react";
import {
  Sparkles,
  Cpu,
  Clock,
  Terminal,
  FileCheck2,
  GitBranch,
  Network,
  FileText,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from "lucide-react";
import {
  InvestigationReport,
  InvestigationEvent,
  Evidence,
  Hypothesis,
} from "@/types";

interface LiveWorkspaceViewProps {
  report: InvestigationReport | null;
  events: InvestigationEvent[];
  onNavigateToGraph: () => void;
  onNavigateToReport: () => void;
}

export function LiveWorkspaceView({
  report,
  events,
  onNavigateToGraph,
  onNavigateToReport,
}: LiveWorkspaceViewProps) {
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);

  if (!report) {
    return (
      <div className="rounded-xl border border-surface-border bg-surface p-12 text-center space-y-3">
        <p className="text-slate-400 text-sm">No active investigation loaded.</p>
        <p className="text-slate-500 text-xs">
          Select a scenario in the "Investigate" tab to start an investigation.
        </p>
      </div>
    );
  }

  const isGeminiMode = report.mode === "AI AGENT MODE";

  return (
    <div className="space-y-6">
      {/* Investigation Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-surface-border bg-surface p-5">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="font-mono text-xs font-bold text-cyan-400">
              {report.investigation_id}
            </span>
            <span
              className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                isGeminiMode
                  ? "bg-emerald-950/60 text-emerald-400 border-emerald-500/40"
                  : "bg-amber-950/60 text-amber-400 border-amber-500/40"
              }`}
            >
              {report.mode}
            </span>
            <span
              className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                report.status === "completed"
                  ? "bg-emerald-950/40 text-emerald-400 border-emerald-500/30"
                  : report.status === "unresolved"
                  ? "bg-amber-950/40 text-amber-400 border-amber-500/30"
                  : "bg-cyan-950/40 text-cyan-400 border-cyan-500/30"
              }`}
            >
              STATUS: {report.status.toUpperCase()}
            </span>
          </div>
          <h2 className="text-base font-bold text-white">{report.failure.title}</h2>
          <p className="text-xs text-slate-300">{report.failure.description}</p>
        </div>

        {/* Quick actions */}
        <div className="flex items-center space-x-2.5">
          <button
            onClick={onNavigateToGraph}
            className="flex items-center space-x-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-3.5 py-2 text-xs font-bold text-cyan-400 hover:bg-cyan-500 hover:text-slate-950 transition-all"
          >
            <Network className="h-3.5 w-3.5" />
            <span>View Causal Graph</span>
          </button>
          <button
            onClick={onNavigateToReport}
            className="flex items-center space-x-1.5 rounded-lg bg-surface-secondary border border-surface-border px-3.5 py-2 text-xs font-bold text-slate-200 hover:text-white hover:bg-surface-border transition-all"
          >
            <FileText className="h-3.5 w-3.5" />
            <span>View Report</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Agent Timeline vs Evidence & Hypotheses */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Real-time Investigation Timeline */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-xl border border-surface-border bg-surface p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div className="flex items-center space-x-2">
                <Terminal className="h-4 w-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">Investigation Trace & Tool Timeline</h3>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">
                {events.length} Events Captured
              </span>
            </div>

            {/* Timeline Stream */}
            <div className="space-y-3">
              {events.map((evt, idx) => {
                const isExpanded = expandedEventId === evt.event_id;
                const hasDetails = evt.tool_args || evt.tool_result;

                return (
                  <div
                    key={evt.event_id}
                    className="rounded-lg border border-surface-border bg-surface-secondary/40 p-3.5 space-y-2 hover:border-surface-highlight transition-all"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-[10px] text-slate-400">
                          {new Date(evt.timestamp).toLocaleTimeString()}
                        </span>
                        <span className="rounded bg-surface-secondary px-2 py-0.5 text-[10px] font-semibold text-cyan-300 border border-surface-border">
                          {evt.stage}
                        </span>
                        {evt.is_gemini_native && (
                          <span className="rounded bg-emerald-950/40 px-1.5 py-0.2 text-[9px] font-bold text-emerald-400 border border-emerald-800/40">
                            GEMINI TOOL CALL
                          </span>
                        )}
                      </div>

                      <span className="text-[10px] font-mono text-slate-500">#{idx + 1}</span>
                    </div>

                    <p className="text-xs text-slate-200 font-medium leading-relaxed">
                      {evt.message}
                    </p>

                    {/* Expandable tool arguments & results */}
                    {hasDetails && (
                      <div className="pt-1">
                        <button
                          onClick={() => setExpandedEventId(isExpanded ? null : evt.event_id)}
                          className="flex items-center space-x-1 text-[11px] font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-3 w-3" />
                          ) : (
                            <ChevronRight className="h-3 w-3" />
                          )}
                          <span>{isExpanded ? "Hide Tool Execution Data" : "Inspect Tool Payload"}</span>
                        </button>

                        {isExpanded && (
                          <div className="mt-2 space-y-2 rounded bg-background p-3 border border-surface-border font-mono text-[11px] text-slate-300 overflow-x-auto">
                            {evt.tool_args && (
                              <div>
                                <span className="text-slate-500 font-bold block mb-1">Tool Inputs:</span>
                                <pre className="text-cyan-300 whitespace-pre-wrap">
                                  {JSON.stringify(evt.tool_args, null, 2)}
                                </pre>
                              </div>
                            )}

                            {evt.tool_result && (
                              <div className="pt-2 border-t border-surface-secondary">
                                <span className="text-slate-500 font-bold block mb-1">Tool Result:</span>
                                <pre className="text-emerald-300 whitespace-pre-wrap">
                                  {JSON.stringify(evt.tool_result, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column (1 Col): Evidence Collection & Hypotheses */}
        <div className="space-y-4">
          {/* Hypotheses Card */}
          <div className="rounded-xl border border-surface-border bg-surface p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <Sparkles className="h-4 w-4 text-cyan-400" />
              <span>Hypotheses Evaluated</span>
            </h3>

            <div className="space-y-2.5">
              {report.hypotheses.map((hyp) => (
                <div
                  key={hyp.id}
                  className="rounded-lg bg-surface-secondary/50 p-3 border border-surface-border space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs text-white">{hyp.title}</span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[9px] font-bold border ${
                        hyp.status === "supported"
                          ? "bg-emerald-950/60 text-emerald-400 border-emerald-500/40"
                          : hyp.status === "refuted"
                          ? "bg-rose-950/60 text-rose-400 border-rose-500/40"
                          : "bg-amber-950/60 text-amber-400 border-amber-500/40"
                      }`}
                    >
                      {hyp.status.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-normal">{hyp.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Collected Evidence Card */}
          <div className="rounded-xl border border-surface-border bg-surface p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <FileCheck2 className="h-4 w-4 text-cyan-400" />
                <span>Collected Evidence Items</span>
              </h3>
              <span className="text-[11px] text-slate-400 font-mono">
                {report.evidence.length} Items
              </span>
            </div>

            <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
              {report.evidence.map((ev) => (
                <div
                  key={ev.id}
                  onClick={() => setSelectedEvidence(selectedEvidence?.id === ev.id ? null : ev)}
                  className={`rounded-lg p-2.5 border cursor-pointer transition-all space-y-1 ${
                    selectedEvidence?.id === ev.id
                      ? "bg-surface-secondary border-cyan-400"
                      : "bg-surface-secondary/40 border-surface-border hover:border-surface-highlight"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] text-cyan-400 font-bold">{ev.id}</span>
                    <span className="text-[9px] font-semibold text-slate-400 uppercase">
                      {ev.type}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-white">{ev.title}</p>
                  <p className="text-[11px] text-slate-300 line-clamp-2">{ev.description}</p>

                  {/* Expanded evidence details */}
                  {selectedEvidence?.id === ev.id && ev.metadata && (
                    <div className="mt-2 pt-2 border-t border-surface-border text-[10px] font-mono text-slate-300 bg-background/60 p-2 rounded">
                      <pre className="whitespace-pre-wrap">
                        {JSON.stringify(ev.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
