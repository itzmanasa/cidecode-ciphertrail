import { motion, AnimatePresence } from "framer-motion";
import { X, ArrowDownCircle, ArrowUpCircle, Network } from "lucide-react";
import type { GraphNode, GraphEdge } from "../../types";
import { Badge } from "../ui/Badge";
import { formatINR, riskColor } from "../../utils/format";

export function NodeInspector({
  node,
  edges,
  onClose,
}: {
  node: GraphNode | null;
  edges: GraphEdge[];
  onClose: () => void;
}) {
  if (!node) return null;
  const connected = edges.filter((e) => e.source === node.id || e.target === node.id);
  const { bg, text } = riskColor(node.risk);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ x: 360, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 360, opacity: 0 }}
        transition={{ type: "spring", stiffness: 280, damping: 30 }}
        className="absolute right-0 top-0 z-10 h-full w-[320px] overflow-y-auto border-l border-ink-100 bg-white/95 glass p-5 shadow-card"
      >
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[11px] font-medium text-ink-500">Account</p>
            <h3 className="text-base font-bold text-ink-900">{node.label || node.id}</h3>
          </div>
          <button onClick={onClose} className="flex h-7 w-7 items-center justify-center rounded-lg text-ink-400 hover:bg-ink-100">
            <X className="h-4 w-4" />
          </button>
        </div>

        <Badge tone="neutral" className={`mt-3 ${bg} ${text}`}>
          {(node.risk || "low").toString().toUpperCase()} RISK
        </Badge>

        <div className="mt-5 grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-success-50 p-3">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-success">
              <ArrowDownCircle className="h-3.5 w-3.5" /> Total Inflow
            </div>
            <p className="mt-1 text-sm font-bold text-ink-900">{formatINR(node.total_inflow as number)}</p>
          </div>
          <div className="rounded-xl bg-danger-50 p-3">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-danger">
              <ArrowUpCircle className="h-3.5 w-3.5" /> Total Outflow
            </div>
            <p className="mt-1 text-sm font-bold text-ink-900">{formatINR(node.total_outflow as number)}</p>
          </div>
        </div>

        <div className="mt-5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-ink-700">
            <Network className="h-3.5 w-3.5 text-primary-500" /> Connected Accounts ({connected.length})
          </div>
          <div className="mt-2 space-y-2">
            {connected.length === 0 && <p className="text-xs text-ink-500">No connected transfers.</p>}
            {connected.map((e, i) => {
              const other = e.source === node.id ? e.target : e.source;
              const direction = e.source === node.id ? "→" : "←";
              return (
                <div key={i} className="flex items-center justify-between rounded-lg border border-ink-100 px-2.5 py-2 text-xs">
                  <span className="font-medium text-ink-700">{direction} {other}</span>
                  <span className="font-mono text-ink-500">{formatINR(e.amount)}</span>
                </div>
              );
            })}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
