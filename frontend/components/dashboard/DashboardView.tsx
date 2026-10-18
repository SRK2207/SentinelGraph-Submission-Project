"use client";

import React from "react";
import {
  ShieldAlert,
  Search,
  CheckCircle2,
  AlertTriangle,
  Server,
  ArrowRight,
  GitCommit,
  Workflow,
  Sparkles,
} from "lucide-react";
import { DashboardStats } from "@/types";

interface DashboardViewProps {
  stats: DashboardStats | null;
  onStartInvestigation: () => void;
  onSelectInvestigation: (id: string) => void;
  onNavigateToConnections: () => void;
}

export function DashboardView({
  stats,
  onStartInvestigation,
  onSelectInvestigation,
  onNavigateToConnections,
}: DashboardViewProps) {
  return (
    <div className="space-y-6">
      {/* Hero Tagline Card */}
      <div className="relative overflow-hidden rounded-xl border border-surface-border bg-gradient-to-r from-surface via-surface-highlight/30 to-surface p-6 sm:p-8">
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center space-x-2 rounded-full bg-cyan-950/60 px-3 py-1 border border-cyan-800/40 text-xs font-semibold text-cyan-400">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Agentic Cross-System Failure Investigation</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            "A change happened here. Something broke there.{" "}
            <span className="text-cyan-400">SentinelGraph investigates why."</span>
          </h1>
          <p className="text-sm text-slate-300 leading-relaxed">
            When a backend modification silently breaks a dependent automation workflow, developers
            waste hours piecing together git logs, API schemas, and orchestration traces.
            SentinelGraph autonomously collects cross-system evidence, verifies causal relationships,
            and pinpoints root causes with evidence-backed provenance.
          </p>
          <div className="pt-2 flex flex-wrap gap-3">
            <button
              onClick={onStartInvestigation}
              className="inline-flex items-center space-x-2 rounded-lg bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-400 transition-all shadow-md shadow-cyan-500/20"
            >
              <Search className="h-4 w-4" />
              <span>Start Investigation</span>
            </button>
            <button
              onClick={onNavigateToConnections}
              className="inline-flex items-center space-x-2 rounded-lg border border-surface-border bg-surface-secondary px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-surface-border transition-all"
            >
              <Server className="h-4 w-4" />
              <span>View Connected Systems</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Investigations */}
        <div className="rounded-xl border border-surface-border bg-surface p-4">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Total Investigations</span>
            <Search className="h-4 w-4 text-cyan-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-white">{stats?.total_investigations ?? 0}</p>
          <p className="mt-1 text-[11px] text-slate-400">Recorded across test suites</p>
        </div>

        {/* Root-Causes Confirmed */}
        <div className="rounded-xl border border-surface-border bg-surface p-4">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Root-Cause Confirmed</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-400">
            {stats?.resolved_investigations ?? 0}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">Supported by verified evidence</p>
        </div>

        {/* Unresolved / Uncertain */}
        <div className="rounded-xl border border-surface-border bg-surface p-4">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Unresolved / Insufficient</span>
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-400">
            {stats?.unresolved_investigations ?? 0}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">Reported uncertainty honestly</p>
        </div>

        {/* Connected Systems */}
        <div className="rounded-xl border border-surface-border bg-surface p-4">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Active Connections</span>
            <Server className="h-4 w-4 text-cyan-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-cyan-400">
            {stats?.active_connections ?? 4}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">Simulated / Mock Data Active</p>
        </div>
      </div>

      {/* Featured Primary Scenario Card */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-rose-950/60 text-rose-400 border border-rose-800/40">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <h2 className="text-sm font-bold text-white">Target Demonstration Scenario</h2>
          </div>
          <span className="rounded bg-accent-blue/20 px-2 py-0.5 text-[10px] font-bold text-cyan-400 border border-accent-blue/30">
            PRIMARY SCENARIO
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 rounded-lg bg-surface-secondary/60 border border-surface-border">
          <div className="space-y-1">
            <div className="flex items-center space-x-1.5 text-xs text-slate-400">
              <Workflow className="h-3.5 w-3.5 text-cyan-400" />
              <span className="font-semibold text-slate-300">Invoice Customer Dispatcher</span>
            </div>
            <p className="text-xs text-rose-400 font-mono">
              KeyError: 'customer_email' was not found
            </p>
            <p className="text-[11px] text-slate-400">
              Trigger: Scheduled monthly billing invoice run
            </p>
          </div>

          <div className="space-y-1">
            <div className="flex items-center space-x-1.5 text-xs text-slate-400">
              <GitCommit className="h-3.5 w-3.5 text-accent-blue" />
              <span className="font-semibold text-slate-300">Recent Customer API Refactor</span>
            </div>
            <p className="text-xs text-slate-300">
              Commit 4f8a12d renamed <code className="text-cyan-300">customer_email</code> &rarr; <code className="text-cyan-300">email</code>
            </p>
            <p className="text-[11px] text-slate-400">
              Deployed successfully without schema notification
            </p>
          </div>

          <div className="flex items-center justify-end">
            <button
              onClick={onStartInvestigation}
              className="flex items-center space-x-1.5 rounded-lg bg-cyan-500/20 px-4 py-2 text-xs font-bold text-cyan-400 border border-cyan-500/40 hover:bg-cyan-500 hover:text-slate-950 transition-all"
            >
              <span>Investigate Failure</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Recent Investigations List */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 space-y-4">
        <h2 className="text-sm font-bold text-white">Recent Failure Investigations</h2>

        {stats && stats.recent_investigations && stats.recent_investigations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-border text-slate-400">
                <tr>
                  <th className="pb-2 font-medium">Investigation ID</th>
                  <th className="pb-2 font-medium">Workflow</th>
                  <th className="pb-2 font-medium">Mode</th>
                  <th className="pb-2 font-medium">Identified Root Cause</th>
                  <th className="pb-2 font-medium">Confidence Assessment</th>
                  <th className="pb-2 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/50 text-slate-300">
                {stats.recent_investigations.map((inv) => (
                  <tr key={inv.investigation_id} className="hover:bg-surface-secondary/40 transition-colors">
                    <td className="py-3 font-mono font-semibold text-cyan-400">
                      {inv.investigation_id}
                    </td>
                    <td className="py-3 font-mono text-slate-300">{inv.workflow}</td>
                    <td className="py-3">
                      <span className="rounded bg-surface-secondary px-2 py-0.5 text-[10px] font-semibold text-slate-300 border border-surface-border">
                        {inv.mode}
                      </span>
                    </td>
                    <td className="py-3 max-w-xs truncate text-white">{inv.root_cause}</td>
                    <td className="py-3">
                      <span
                        className={`rounded px-2 py-0.5 text-[10px] font-semibold border ${
                          inv.status === "completed"
                            ? "bg-emerald-950/40 text-emerald-400 border-emerald-500/40"
                            : "bg-amber-950/40 text-amber-400 border-amber-500/40"
                        }`}
                      >
                        {inv.confidence_label}
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => onSelectInvestigation(inv.investigation_id)}
                        className="rounded px-2.5 py-1 text-[11px] font-semibold text-cyan-400 hover:bg-cyan-500/20 border border-cyan-500/30 transition-all"
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-slate-500 text-xs">
            No investigations run yet in this session. Click "Start Investigation" to begin.
          </div>
        )}
      </div>
    </div>
  );
}
