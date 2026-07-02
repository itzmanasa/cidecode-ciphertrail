import { useMemo } from "react";
import ReactFlow, { Background, MarkerType, type Node, type Edge } from "reactflow";
import "reactflow/dist/style.css";

export function LoopMiniGraph({ accounts }: { accounts: string[] }) {
  const { nodes, edges } = useMemo(() => {
    const radius = 110;
    const n: Node[] = accounts.map((acc, i) => {
      const angle = (2 * Math.PI * i) / accounts.length - Math.PI / 2;
      return {
        id: `${acc}-${i}`,
        position: { x: 150 + radius * Math.cos(angle), y: 110 + radius * Math.sin(angle) },
        data: { label: acc },
        style: {
          fontSize: 10,
          fontWeight: 600,
          borderRadius: 10,
          border: "1px solid #E0E7FF",
          background: "#fff",
          padding: 6,
          color: "#334155",
        },
      };
    });

    const e: Edge[] = accounts.map((acc, i) => {
      const nextIdx = (i + 1) % accounts.length;
      return {
        id: `loop-${i}`,
        source: `${acc}-${i}`,
        target: `${accounts[nextIdx]}-${nextIdx}`,
        animated: true,
        style: { stroke: "#EF4444", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#EF4444" },
      };
    });

    return { nodes: n, edges: e };
  }, [accounts]);

  return (
    <div className="h-[220px] w-full rounded-xl border border-ink-100 bg-bg-soft">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#E2E8F0" gap={16} />
      </ReactFlow>
    </div>
  );
}
