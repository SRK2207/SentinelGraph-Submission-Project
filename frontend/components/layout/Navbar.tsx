"use client";

import React from "react";
import {
  ShieldAlert,
  RotateCcw,
  Sparkles,
  Server,
  Activity,
  GitBranch,
  FileText,
  Network,
} from "lucide-react";
import { HealthStatus } from "@/types";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  health: HealthStatus | null;
  onResetDemo: () => void;
  isResetting: boolean;
  hasActiveInvestigation: boolean;
}

export function Navbar({
  activeTab,
  setActiveTab,
  health,
  onResetDemo,
  isResetting,
  hasActiveInvestigation,
}: NavbarProps) {
  const isAiMode = health?.gemini_configured ?? false;

  const navItems = [
    { id: "dashboard", label: "Dashboard", shortLabel: "Dashboard", icon: Activity },
    { id: "investigate", label: "Investigate", shortLabel: "Investigate", icon: ShieldAlert },
    {
      id: "workspace",
      label: "Live Workspace",
      shortLabel: "Workspace",
      icon: Sparkles,
      disabled: !hasActiveInvestigation,
    },
    {
      id: "graph",
      label: "Causal Graph",
      shortLabel: "Graph",
      icon: Network,
      disabled: !hasActiveInvestigation,
    },
    {
      id: "report",
      label: "Report & Remediation",
      shortLabel: "Report",
      icon: FileText,
      disabled: !hasActiveInvestigation,
    },
    { id: "connections", label: "Connections", shortLabel: "Connections", icon: Server },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-surface-border bg-background/95 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 gap-3 sm:gap-6">
        {/* Brand */}
        <div className="flex items-center space-x-3 flex-shrink-0">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
            <ShieldAlert className="h-6 w-6 text-slate-950" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-lg font-bold tracking-tight text-white">
                Sentinel<span className="text-cyan-400">Graph</span>
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium hidden sm:block">
              Cross-System Failure Investigation Platform
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center space-x-1 rounded-lg bg-surface p-1 border border-surface-border flex-shrink">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => !item.disabled && setActiveTab(item.id)}
                disabled={item.disabled}
                className={`flex items-center space-x-1.5 rounded-md px-2.5 lg:px-3 py-1.5 text-xs font-medium transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-accent-blue/20 text-cyan-400 border border-accent-blue/40 shadow-sm"
                    : item.disabled
                    ? "cursor-not-allowed text-slate-600"
                    : "text-slate-300 hover:bg-surface-secondary hover:text-white"
                }`}
              >
                <Icon className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="hidden lg:inline">{item.label}</span>
                <span className="inline lg:hidden">{item.shortLabel}</span>
              </button>
            );
          })}
        </nav>

        {/* Actions & Status Pill */}
        <div className="flex items-center space-x-3 sm:space-x-4 flex-shrink-0 ml-auto md:ml-0">
          {/* Mode Pill */}
          <div
            className={`flex items-center space-x-2 rounded-full px-3 py-1.5 text-[11px] font-semibold border whitespace-nowrap shadow-sm ${
              isAiMode
                ? "bg-emerald-950/40 text-emerald-400 border-emerald-500/40"
                : "bg-amber-950/40 text-amber-400 border-amber-500/40"
            }`}
            title={
              isAiMode
                ? `Running live Gemini agent with model: ${health?.gemini_model}`
                : "Deterministic Demo Mode enabled (safe local evaluation)"
            }
          >
            <span
              className={`h-2 w-2 rounded-full flex-shrink-0 ${
                isAiMode ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              }`}
            />
            <span>{isAiMode ? "AI AGENT MODE" : "DETERMINISTIC DEMO MODE"}</span>
          </div>

          {/* Reset Demo Button */}
          <button
            onClick={onResetDemo}
            disabled={isResetting}
            className="flex items-center space-x-1.5 rounded-md border border-surface-border bg-surface px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-surface-secondary hover:text-white transition-all disabled:opacity-50 whitespace-nowrap flex-shrink-0"
            title="Reset synthetic fixtures and in-memory investigations"
          >
            <RotateCcw className={`h-3.5 w-3.5 ${isResetting ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Reset State</span>
          </button>
        </div>
      </div>

      {/* Mobile Navigation bar */}
      <div className="flex md:hidden overflow-x-auto border-t border-surface-border px-2 py-1.5 bg-surface gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => !item.disabled && setActiveTab(item.id)}
              disabled={item.disabled}
              className={`flex items-center space-x-1 whitespace-nowrap rounded px-2.5 py-1 text-xs font-medium ${
                isActive
                  ? "bg-accent-blue/20 text-cyan-400"
                  : item.disabled
                  ? "text-slate-600"
                  : "text-slate-300"
              }`}
            >
              <Icon className="h-3 w-3" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
}
