"use client";

import { useEffect, useMemo, useState } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { api, type CodeGraph } from "@/lib/api";

export default function ServiceGraph({ projectId }: { projectId: string }) {
  const [graph, setGraph] = useState<CodeGraph | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.graph(projectId).then(setGraph).catch((e) => setError(String(e)));
  }, [projectId]);

  const { nodes, edges } = useMemo(() => {
    if (!graph) return { nodes: [] as Node[], edges: [] as Edge[] };
    const nodes: Node[] = graph.nodes.map((n, i) => ({
      id: n.id,
      data: { label: `${n.name}\n(${n.node_type})` },
      position: { x: 80 + (i % 2) * 280, y: 80 + i * 90 },
      style: {
        background: "#1c1c1c",
        color: "#e5e5e5",
        border: "1px solid #2f6f4f",
        borderRadius: 8,
        fontSize: 12,
        whiteSpace: "pre-line",
        width: 180,
      },
    }));
    const edges: Edge[] = graph.edges.map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      animated: true,
      style: { stroke: "#2f6f4f" },
    }));
    return { nodes, edges };
  }, [graph]);

  if (error) return <p className="text-sm text-red-400">{error}</p>;

  return (
    <div className="h-[calc(100vh-12rem)] rounded-lg border border-neutral-800">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#333" />
        <Controls />
      </ReactFlow>
    </div>
  );
}
