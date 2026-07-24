"use client";
import { ReactFlow, Background, Controls, MiniMap, MarkerType, Node, Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";

const TYPE_COLOR: Record<string, string> = {
  person: "#00f0ff", email: "#8b5cf6", phone: "#ff2bd6", username: "#34d399",
  domain: "#60a5fa", ip: "#f59e0b", website: "#a78bfa", company: "#fb923c",
  root: "#ff4d6d",
};

export function GraphCanvas({ nodes, edges, height = 540 }: { nodes: any[]; edges: any[]; height?: number }) {
  const rfNodes: Node[] = useMemo(
    () => nodes.map((n) => ({
      id: n.id,
      position: { x: 0, y: 0 },
      data: { label: `${n.label}` },
      type: "default",
      style: {
        background: "rgba(15,23,42,0.85)",
        color: "#e2e8f0",
        border: `1px solid ${TYPE_COLOR[n.type] || "#475569"}`,
        borderRadius: 10,
        fontSize: 12,
        padding: 8,
        boxShadow: "0 0 24px rgba(0,0,0,0.5)",
        whiteSpace: "nowrap",
      },
    })),
    [nodes],
  );
  const rfEdges: Edge[] = useMemo(
    () => edges.map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      label: e.label || undefined,
      animated: true,
      style: { stroke: "#00f0ff", strokeOpacity: 0.55 },
      labelStyle: { fill: "#cbd5e1", fontSize: 10 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#00f0ff" },
    })),
    [edges],
  );

  return (
    <div style={{ height }} className="rounded-xl overflow-hidden border border-white/10 bg-black/40">
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={{ type: "smoothstep" }}
      >
        <Background gap={30} color="rgba(0,240,255,0.12)" />
        <Controls className="!bg-black/60 !border-white/10" />
        <MiniMap
          pannable zoomable
          maskColor="rgba(2,6,23,0.7)"
          nodeStrokeWidth={3}
          nodeColor={(n) => {
            const found = nodes.find((x) => x.id === n.id);
            return TYPE_COLOR[found?.type] || "#475569";
          }}
        />
      </ReactFlow>
    </div>
  );
}
