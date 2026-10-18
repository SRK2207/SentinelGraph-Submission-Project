"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  Play,
  Sparkles,
  Cpu,
  Clock,
  Workflow,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { ScenarioOverview, HealthStatus } from "@/types";

interface ScenarioSelectViewProps {
  scenarios: ScenarioOverview[];
  health: HealthStatus | null;
  onLaunchInvestigation: (scenarioId: string, forceDeterministic: boolean) => void;
  isLoading: boolean;
}

export function ScenarioSelectView({
  scenarios,
  health,
  onLaunchInvestigation,
  isLoading,
}: ScenarioSelectViewProps) {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(
    "scenario-invoice-field-rename"
  );
  const [forceDeterministic, setForceDeterministic] = useState<boolean>(false);

  const isGeminiAvailable = health?.gemini_configured ?? false;

  const handleLaunch = () => {
    onLaunchInvestigation(selectedScenarioId, forceDeterministic);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-2">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="h-5 w-5 text-cyan-400" />
          <h1 className="text-xl font-bold text-white">Select Investigation Scenario</h1>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          Choose a failure incident to investigate. SentinelGraph's agent will autonomously query
          failure details, inspect recent commits, trace dependency contracts, and construct an
          evidence-backed causal graph.
        </p>
      </div>

      {/* Scenarios Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {scenarios.map((sc) => {
          const isSelected = selectedScenarioId === sc.id;
          const isPrimary = sc.id === "scenario-invoice-field-rename";

          return (
            <div
              key={sc.id}
              onClick={() => setSelectedScenarioId(sc.id)}
              className={`cursor-pointer rounded-xl border p-5 space-y-4 transition-all relative ${
                isSelected
                  ? "bg-surface-secondary border-cyan-400/80 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-400/40"
                  : "bg-surface border-surface-border hover:border-surface-highlight hover:bg-surface/80"
              }`}
            >
              {/* Badges */}
              <div className="flex items-center justify-between">
                <span
                  className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                    isPrimary
                      ? "bg-cyan-950/60 text-cyan-400 border-cyan-800/40"
                      : "bg-amber-950/60 text-amber-400 border-amber-800/40"
                  }`}
                >
                  {isPrimary ? "(RECOMMENDED) PRIMARY DEMO" : "AMBIGUOUS / UNCERTAINTY TEST"}
                </span>

                <div className="flex items-center space-x-1.5 text-slate-400 text-[11px]">
                  <Clock className="h-3 w-3" />
                  <span>{new Date(sc.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>

              {/* Title & Desc */}
              <div>
                <h3 className="text-sm font-bold text-white">{sc.name}</h3>
                <p className="mt-1 text-xs text-slate-300 leading-normal">{sc.description}</p>
              </div>

              {/* Incident Details Card */}
              <div className="rounded-lg bg-surface/80 p-3 border border-surface-border space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 font-medium">Affected Workflow:</span>
                  <span className="font-mono text-cyan-300 font-semibold">{sc.workflow_name}</span>
                </div>

                <div className="space-y-0.5">
                  <span className="text-slate-400 font-medium">Error Trigger:</span>
                  <p className="font-mono text-[11px] text-rose-400 bg-rose-950/30 p-1.5 rounded border border-rose-900/40">
                    {sc.error_message}
                  </p>
                </div>
              </div>

              {/* Selection Checkmark */}
              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] text-slate-400">Category: {sc.category}</span>
                <div
                  className={`flex h-5 w-5 items-center justify-center rounded-full border ${
                    isSelected
                      ? "border-cyan-400 bg-cyan-400 text-slate-950"
                      : "border-slate-600 bg-transparent"
                  }`}
                >
                  {isSelected && <CheckCircle2 className="h-4 w-4 stroke-[3]" />}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Mode Configuration & Launch Action */}
      <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-5">
        <h2 className="text-sm font-bold text-white flex items-center space-x-2">
          <Cpu className="h-4 w-4 text-cyan-400" />
          <span>Investigation Mode & Execution Settings</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {/* Mode Option 1: AI Agent Mode */}
          <div
            onClick={() => isGeminiAvailable && setForceDeterministic(false)}
            className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
              !forceDeterministic && isGeminiAvailable
                ? "bg-surface-secondary border-emerald-500/60 ring-1 ring-emerald-500/30"
                : !isGeminiAvailable
                ? "opacity-50 cursor-not-allowed border-surface-border bg-surface"
                : "border-surface-border bg-surface hover:bg-surface-secondary/40"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-white flex items-center space-x-1.5">
                <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                <span>Gemini AI Agent Mode</span>
              </span>
              <span
                className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                  isGeminiAvailable
                    ? "bg-emerald-950/60 text-emerald-400"
                    : "bg-slate-800 text-slate-400"
                }`}
              >
                {isGeminiAvailable ? "AVAILABLE" : "KEY REQUIRED"}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400 leading-normal">
              Uses live Google GenAI SDK function calling with model{" "}
              <code className="text-slate-300">{health?.gemini_model || "gemini-2.5-flash"}</code>.
            </p>
          </div>

          {/* Mode Option 2: Deterministic Demo Mode */}
          <div
            onClick={() => setForceDeterministic(true)}
            className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
              forceDeterministic || !isGeminiAvailable
                ? "bg-surface-secondary border-amber-500/60 ring-1 ring-amber-500/30"
                : "border-surface-border bg-surface hover:bg-surface-secondary/40"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-white flex items-center space-x-1.5">
                <Cpu className="h-3.5 w-3.5 text-amber-400" />
                <span>Deterministic Demo Mode</span>
              </span>
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-950/60 text-amber-400">
                OFFLINE READY
              </span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400 leading-normal">
              Executes identical tool-calling trace deterministically. Works locally without requiring
              API keys or network connectivity.
            </p>
          </div>
        </div>

        {/* Launch Button */}
        <div className="pt-2 flex items-center justify-end">
          <button
            onClick={handleLaunch}
            disabled={isLoading}
            className="flex items-center space-x-2 rounded-lg bg-cyan-500 px-6 py-2.5 text-sm font-bold text-slate-950 hover:bg-cyan-400 transition-all shadow-lg shadow-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
                <span>Investigating Incident...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-slate-950" />
                <span>Launch Autonomous Investigation</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
