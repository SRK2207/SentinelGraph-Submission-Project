"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  MarkerType,
  Node,
  Edge,
} from "@xyflow/react";
import {
  Network,
  GitCommit,
  Server,
  Workflow,
  AlertOctagon,
  FileCheck2,
  Info,
  Maximize2,
  HelpCircle,
  ExternalLink,
} from "lucide-react";
import { GraphData, GraphNodeData, Evidence } from "@/types";

// Custom node component for React Flow
function SentinelNodeComponent({
  data,
  selected,
}: {
  data: GraphNodeData;
  selected?: boolean;
}) {
  const getIcon = (ctype: string) => {
    switch (ctype) {
      case "commit":
        return GitCommit;
      case "api_schema":
        return Server;
      case "workflow_step":
        return Workflow;
      case "failure":
        return AlertOctagon;
      default:
        return Server;
    }
  };

  const getStatusBorder = (status: string) => {
    switch (status) {
      case "confirmed":
        return "border-cyan-500/80 shadow-cyan-500/20";
      case "probable_cause":
        return "border-amber-400/90 shadow-amber-400/30 ring-1 ring-amber-400/50";
      case "affected_component":
        return "border-rose-500/80 shadow-rose-500/20";
      case "unverified_hypothesis":
        return "border-dashed border-slate-500 shadow-slate-500/10";
      default:
        return "border-slate-600";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "confirmed":
        return { text: "CONFIRMED FACT", bg: "bg-cyan-950/60 text-cyan-400 border-cyan-700/50" };
      case "probable_cause":
        return { text: "PROBABLE CAUSE", bg: "bg-amber-950/60 text-amber-400 border-amber-700/50 animate-pulse" };
      case "affected_component":
        return { text: "AFFECTED COMPONENT", bg: "bg-rose-950/60 text-rose-400 border-rose-700/50" };
      case "unverified_hypothesis":
        return { text: "UNVERIFIED HYPOTHESIS", bg: "bg-slate-800 text-slate-400 border-slate-600" };
      default:
        return { text: status, bg: "bg-slate-800 text-slate-300 border-slate-600" };
    }
  };

  const Icon = getIcon(data.component_type);
  const badge = getStatusBadge(data.status);

  return (
    <div
      className={`relative w-72 rounded-xl bg-surface p-4 border text-left shadow-lg transition-all ${
        getStatusBorder(data.status)
      } ${selected ? "ring-2 ring-cyan-400 scale-[1.02]" : ""}`}
    >
      <Handle type="target" position={Position.Left} className="!bg-cyan-400 !w-2.5 !h-2.5" />
      <Handle type="source" position={Position.Right} className="!bg-cyan-400 !w-2.5 !h-2.5" />

      <div className="space-y-2">
        {/* Top Type & Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-1.5 text-slate-400">
            <Icon className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-[10px] font-mono uppercase tracking-wider">
              {data.component_type.replace("_", " ")}
            </span>
          </div>

          <span className={`rounded px-1.5 py-0.5 text-[8px] font-bold border ${badge.bg}`}>
            {badge.text}
          </span>
        </div>

        {/* Title */}
        <h4 className="text-xs font-bold text-white line-clamp-1">{data.label}</h4>

        {/* Short explanation */}
        <p className="text-[11px] text-slate-300 leading-normal line-clamp-2">
          {data.explanation}
        </p>

        {/* Evidence badge footer */}
        {data.evidence_ids && data.evidence_ids.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1 border-t border-surface-border">
            {data.evidence_ids.map((id) => (
              <span
                key={id}
                className="font-mono text-[9px] bg-surface-secondary px-1 py-0.5 rounded text-cyan-300 border border-surface-border"
              >
                {id}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const nodeTypes = {
  customSentinel: SentinelNodeComponent,
};

interface CausalGraphViewProps {
  graphData: GraphData | null;
  evidenceList: Evidence[];
}

export function CausalGraphView({ graphData, evidenceList }: CausalGraphViewProps) {
  const [selectedNodeData, setSelectedNodeData] = useState<GraphNodeData | null>(null);

  // Initial nodes and edges formatted for React Flow
  const initialNodes: Node[] = useMemo(() => {
    if (!graphData) return [];
    return graphData.nodes.map((n) => ({
      id: n.id,
      type: "customSentinel",
      position: n.position,
      data: n.data,
    }));
  }, [graphData]);

  const initialEdges: Edge[] = useMemo(() => {
    if (!graphData) return [];
    return graphData.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      animated: e.animated,
      style: { stroke: "#06b6d4", strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: "#06b6d4",
      },
    }));
  }, [graphData]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    if (initialNodes.length > 0) {
      setSelectedNodeData(initialNodes[0].data as GraphNodeData);
    }
  }, [initialNodes, initialEdges]);

  const handleNodeClick = (_: any, node: Node) => {
    setSelectedNodeData(node.data as GraphNodeData);
  };

  const evidenceMap = useMemo(() => {
    const map = new Map<string, Evidence>();
    for (const ev of evidenceList) {
      map.set(ev.id, ev);
    }
    return map;
  }, [evidenceList]);

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="rounded-xl border border-surface-border bg-surface p-12 text-center space-y-3">
        <p className="text-slate-400 text-sm">No causal graph available yet.</p>
        <p className="text-slate-500 text-xs">Run an investigation to generate the causal graph.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header & Legend */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-surface-border bg-surface p-4">
        <div>
          <h2 className="text-sm font-bold text-white flex items-center space-x-2">
            <Network className="h-4 w-4 text-cyan-400" />
            <span>Interactive Causal Dependency Graph</span>
          </h2>
          <p className="text-[11px] text-slate-400">
            Constructed by backend NetworkX engine. Click any node to inspect evidence provenance.
          </p>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold">
          <span className="flex items-center space-x-1 rounded bg-cyan-950/60 px-2 py-0.5 text-cyan-400 border border-cyan-800/40">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            <span>Fact</span>
          </span>
          <span className="flex items-center space-x-1 rounded bg-amber-950/60 px-2 py-0.5 text-amber-400 border border-amber-800/40">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            <span>Probable Cause</span>
          </span>
          <span className="flex items-center space-x-1 rounded bg-rose-950/60 px-2 py-0.5 text-rose-400 border border-rose-800/40">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
            <span>Affected</span>
          </span>
        </div>
      </div>

      {/* Main Canvas + Inspector Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* React Flow Canvas (3 Cols) */}
        <div className="lg:col-span-3 h-[580px] rounded-xl border border-surface-border bg-background relative overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onNodeClick={handleNodeClick}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            minZoom={0.2}
            maxZoom={1.8}
          >
            <Background color="#1e293b" gap={18} size={1} />
            <Controls className="!bg-surface !border-surface-border" />
            <MiniMap
              nodeColor={(node) => {
                const status = (node.data as any)?.status;
                if (status === "probable_cause") return "#f59e0b";
                if (status === "affected_component") return "#f43f5e";
                return "#06b6d4";
              }}
              className="!bg-surface/90 !border-surface-border"
            />
          </ReactFlow>
        </div>

        {/* Selected Node Inspector Sidebar (1 Col) */}
        <div className="rounded-xl border border-surface-border bg-surface p-5 space-y-4">
          <div className="flex items-center space-x-2 border-b border-surface-border pb-3">
            <Info className="h-4 w-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">Node Inspector</h3>
          </div>

          {selectedNodeData ? (
            <div className="space-y-4">
              <div>
                <span className="text-[10px] uppercase font-mono text-cyan-400 tracking-wider">
                  {selectedNodeData.component_type.replace("_", " ")}
                </span>
                <h4 className="text-sm font-bold text-white mt-0.5">{selectedNodeData.label}</h4>
              </div>

              <div className="p-3 rounded-lg bg-surface-secondary/70 border border-surface-border space-y-1">
                <span className="text-[10px] uppercase font-semibold text-slate-400 block">
                  Status & Relationship
                </span>
                <p className="text-xs text-slate-200 leading-normal">
                  {selectedNodeData.explanation}
                </p>
              </div>

              {/* Linked Evidence Items */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
                  <FileCheck2 className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Linked Evidence Provenance</span>
                </span>

                {selectedNodeData.evidence_ids && selectedNodeData.evidence_ids.length > 0 ? (
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {selectedNodeData.evidence_ids.map((id) => {
                      const ev = evidenceMap.get(id);
                      return (
                        <div
                          key={id}
                          className="rounded bg-background p-2 border border-surface-border text-xs space-y-1 font-sans"
                        >
                          <div className="flex items-center justify-between font-mono text-[10px]">
                            <span className="text-cyan-400 font-bold">{id}</span>
                            <span className="text-slate-500 uppercase">{ev?.source || "catalog"}</span>
                          </div>
                          <p className="font-semibold text-white text-[11px]">{ev?.title || id}</p>
                          <p className="text-[10px] text-slate-400 line-clamp-2">
                            {ev?.description || "Observed in repository history"}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-[11px] text-slate-500">No linked evidence tags on this node.</p>
                )}
              </div>

              {/* Node Metadata */}
              {selectedNodeData.metadata && Object.keys(selectedNodeData.metadata).length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-xs font-semibold text-slate-300">Technical Attributes</span>
                  <div className="rounded bg-background p-2.5 border border-surface-border font-mono text-[10px] text-slate-300 overflow-x-auto">
                    <pre className="whitespace-pre-wrap">
                      {JSON.stringify(selectedNodeData.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate-400 py-6 text-center">
              Click any node in the graph to view technical details.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
