import { useMemo, useState, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  MarkerType,
  useNodesState,
  useEdgesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { Search, Filter } from "lucide-react";
import { useCase } from "../context/CaseContext";
import { useAnalysis } from "../hooks/useAnalysis";
import { NoActiveCase } from "../components/layout/NoActiveCase";
import { AccountNode } from "../components/moneyflow/AccountNode";
import { NodeInspector } from "../components/moneyflow/NodeInspector";
import { Card } from "../components/ui/Card";
import type { GraphNode, GraphEdge } from "../types";

const nodeTypes = { account: AccountNode };

const RISK_EDGE_COLOR: Record<string, string> = {
  high: "#EF4444",
  critical: "#EF4444",
  medium: "#F59E0B",
  low: "#22C55E",
};

function buildFlow(nodes: GraphNode[], edges: GraphEdge[]) {
  const rfNodes: Node[] = nodes.map((n, i) => ({
    id: n.id,
    type: "account",
    position: { x: (i % 6) * 220, y: Math.floor(i / 6) * 140 },
    data: { label: n.label || n.account || n.id, risk: n.risk },
  }));

  const rfEdges: Edge[] = edges.map((e, i) => {
    const color = RISK_EDGE_COLOR[(e.risk || "low").toLowerCase()] || "#94A3B8";
    return {
      id: e.id || `e-${i}`,
      source: e.source,
      target: e.target,
      label: e.amount ? `₹${Number(e.amount).toLocaleString("en-IN")}` : e.label,
      animated: (e.risk || "").toLowerCase() === "high" || (e.risk || "").toLowerCase() === "critical",
      style: { stroke: color, strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color },
      labelStyle: { fontSize: 10, fill: "#334155", fontWeight: 600 },
      labelBgStyle: { fill: "#fff", fillOpacity: 0.9 },
    };
  });

  return { rfNodes, rfEdges };
}

export function MoneyFlowPage() {
  const { caseId } = useCase();
  const { data, isLoading } = useAnalysis(caseId ?? undefined);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<string>("all");
  const [selected, setSelected] = useState<GraphNode | null>(null);

  const graph = data?.findings?.graph;
  const allNodes = graph?.nodes ?? [];
  const allEdges = graph?.edges ?? [];

  const filteredNodes = useMemo(() => {
    return allNodes.filter((n) => {
      const matchesSearch = !search || (n.label || n.account || n.id).toLowerCase().includes(search.toLowerCase());
      const matchesRisk = riskFilter === "all" || (n.risk || "low").toLowerCase() === riskFilter;
      return matchesSearch && matchesRisk;
    });
  }, [allNodes, search, riskFilter]);

  const { rfNodes, rfEdges } = useMemo(() => buildFlow(filteredNodes, allEdges), [filteredNodes, allEdges]);
  const [nodes, , onNodesChange] = useNodesState(rfNodes);
  const [edges, , onEdgesChange] = useEdgesState(rfEdges);

  const onNodeClick = useCallback(
    (_: unknown, node: Node) => {
      const original = allNodes.find((n) => n.id === node.id) || null;
      setSelected(original);
    },
    [allNodes]
  );

  if (!caseId) return <NoActiveCase />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-900">Money Flow</h1>
          <p className="text-sm text-ink-500">Visual trace of fund movement across accounts</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-300" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search account…"
              className="h-9 rounded-xl border border-ink-100 bg-white pl-8 pr-3 text-xs outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
            />
          </div>
          <div className="relative">
            <Filter className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-300" />
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="h-9 appearance-none rounded-xl border border-ink-100 bg-white pl-8 pr-6 text-xs outline-none focus:border-primary-500"
            >
              <option value="all">All risk</option>
              <option value="high">High risk</option>
              <option value="medium">Medium risk</option>
              <option value="low">Low risk</option>
            </select>
          </div>
        </div>
      </div>

      <Card className="relative h-[640px] overflow-hidden p-0">
        {isLoading ? (
          <div className="skeleton h-full w-full" />
        ) : allNodes.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-ink-500">No graph data available for this case.</div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#E2E8F0" gap={18} />
            <Controls />
            <MiniMap pannable zoomable nodeColor="#C7D2FE" maskColor="rgba(248,250,252,0.7)" />
          </ReactFlow>
        )}

        <NodeInspector node={selected} edges={allEdges} onClose={() => setSelected(null)} />

        <div className="absolute bottom-4 left-4 flex items-center gap-3 rounded-xl border border-ink-100 bg-white/90 glass px-3 py-2 text-[11px] font-medium text-ink-700 shadow-soft">
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-success" /> Low risk</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-warning" /> Medium risk</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-danger" /> High risk</span>
        </div>
      </Card>
    </div>
  );
}
