"use client";

import React from "react";
import {
  Server,
  GitBranch,
  Database,
  Workflow,
  CheckCircle2,
  Info,
  Clock,
  ShieldCheck,
} from "lucide-react";
import { ConnectionStatus } from "@/types";

interface ConnectionsViewProps {
  connections: ConnectionStatus[];
}

export function ConnectionsView({ connections }: ConnectionsViewProps) {
  const getIcon = (id: string) => {
    switch (id) {
      case "conn-git-repo":
        return GitBranch;
      case "conn-backend-api":
        return Server;
      case "conn-schema-catalog":
        return Database;
      case "conn-workflow-engine":
        return Workflow;
      default:
        return Server;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Description & Transparency Notice */}
      <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-3">
        <div className="flex items-center space-x-2">
          <Server className="h-5 w-5 text-cyan-400" />
          <h1 className="text-xl font-bold text-white">Simulated Integration Connectors</h1>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">
          SentinelGraph inspects cross-system boundaries through read-only metadata collectors.
          In this local prototype, external system responses are powered by authoritative synthetic
          fixtures. No live OAuth logins or external API tokens are required.
        </p>

        <div className="flex items-start space-x-2.5 rounded-lg bg-surface-secondary/80 p-3 border border-surface-border text-xs text-slate-400">
          <Info className="h-4 w-4 text-cyan-400 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-slate-200">Prototype Integrity Notice: </span>
            All data below represents local synthetic fixtures used to demonstrate cross-system causal
            tracing without third-party cloud hosting dependencies.
          </div>
        </div>
      </div>

      {/* Connectors Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {connections.map((conn) => {
          const Icon = getIcon(conn.id);
          const isSimulated = conn.status === "SIMULATED";
          const isMock = conn.status === "MOCK DATA";

          return (
            <div
              key={conn.id}
              className="rounded-xl border border-surface-border bg-surface p-5 space-y-4 hover:border-surface-highlight transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-secondary border border-surface-border text-cyan-400">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{conn.name}</h3>
                    <p className="text-[11px] text-slate-400 font-medium">{conn.type}</p>
                  </div>
                </div>

                <span
                  className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                    isSimulated
                      ? "bg-cyan-950/40 text-cyan-400 border-cyan-800/40"
                      : isMock
                      ? "bg-violet-950/40 text-violet-400 border-violet-800/40"
                      : "bg-slate-800 text-slate-400 border-slate-700"
                  }`}
                >
                  {conn.status}
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-normal">{conn.description}</p>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-surface-border text-[11px]">
                <div className="flex items-center space-x-1.5 text-slate-400">
                  <Clock className="h-3.5 w-3.5 text-slate-500" />
                  <span>Last Sync: {conn.last_sync}</span>
                </div>
                <div className="flex items-center justify-end space-x-1.5 text-slate-400">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  <span>{conn.records_available} Entities Monitored</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Production Architecture Roadmap Card */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 space-y-3">
        <h2 className="text-sm font-bold text-white flex items-center space-x-2">
          <ShieldCheck className="h-4 w-4 text-cyan-400" />
          <span>Production Architecture Integration Model</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-slate-300">
          <div className="p-3 rounded-lg bg-surface-secondary/60 border border-surface-border">
            <h4 className="font-semibold text-white mb-1">Git Webhooks & Diffs</h4>
            <p className="text-[11px] text-slate-400">
              Receives push and merge events with commit SHA, author, and per-file unified diffs.
            </p>
          </div>
          <div className="p-3 rounded-lg bg-surface-secondary/60 border border-surface-border">
            <h4 className="font-semibold text-white mb-1">OpenAPI / GraphQL Schemas</h4>
            <p className="text-[11px] text-slate-400">
              Tracks breaking field renames, removals, and payload mutations across staging and prod.
            </p>
          </div>
          <div className="p-3 rounded-lg bg-surface-secondary/60 border border-surface-border">
            <h4 className="font-semibold text-white mb-1">Workflow Orchestrator Traces</h4>
            <p className="text-[11px] text-slate-400">
              Captures step-level error messages, execution logs, and required input payloads.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
