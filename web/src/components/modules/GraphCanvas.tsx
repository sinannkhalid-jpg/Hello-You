"use client";
import { ReactFlow, Background, Controls, MiniMap, MarkerType, Node, Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";

const TYPE_COLOR: Record<string, string> = {
  person: "#ffffff", email: "#a1a1aa", phone: "#a1a1aa", username: "#a1a1aa",
  domain: "#ffffff", ip: "#a1a1aa", website: "#a1a1aa", company: "#a1a1aa",
  root: "#ffffff",
};

export function GraphCanvas({ nodes, edges, height = 540 }: { nodes: any[]; edges: any[]; height?: number }) {
  const rfNodes: Node[] = useMemo(
    () => nodes.map((n) => ({
      id: n.id,
      position: { x: 0, y: 0 },
      data: { label: `${n.label}` },
      type: "default",
      style: {
        background: "#151515",
        color: "#ffffff",
        border: `1px solid ${TYPE_COLOR[n.type] || "#262626"}`,
        borderRadius: 8,
        fontSize: 12,
        padding: 8,
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
      animated: false,
      style: { stroke: "#404040", strokeOpacity: 0.7 },
      labelStyle: { fill: "#a1a1aa", fontSize: 10 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#404040" },
    })),
    [edges],
  );

  return (
    <div style={{ height }} className="rounded-xl overflow-hidden border border-[#262626] bg-[#0a0a0a]">
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={{ type: "smoothstep" }}
      >
        <Background gap={30} color="rgba(255,255,255,0.04)" />
        <Controls className="!bg-[#151515] !border-[#262626]" />
        <MiniMap
          pannable zoomable
          maskColor="rgba(9,9,9,0.8)"
          nodeStrokeWidth={3}
          nodeColor={(n) => {
            const found = nodes.find((x) => x.id === n.id);
            return TYPE_COLOR[found?.type] || "#262626";
          }}
        />
      </ReactFlow>
    </div>
  );
}
