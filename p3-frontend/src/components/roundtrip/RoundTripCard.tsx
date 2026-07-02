import { useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, GitBranch, Clock, ArrowRightLeft } from "lucide-react";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import type { RoundTrip } from "../../types";
import { formatINR, riskColor } from "../../utils/format";
import { LoopMiniGraph } from "./LoopMiniGraph";

export function RoundTripCard({ loop, index }: { loop: RoundTrip; index: number }) {
  const [open, setOpen] = useState(false);
  const { bg, text } = riskColor(loop.risk);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.04 }}>
      <Card className="overflow-hidden">
        <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left">
          <div className="flex items-center gap-3 min-w-0">
            <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${bg} ${text}`}>
              <GitBranch className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink-900">Loop {loop.loop_id}</p>
              <p className="truncate text-xs text-ink-500">
                {loop.accounts.join(" → ")} → {loop.accounts[0]}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-bold text-ink-900">{formatINR(loop.amount)}</p>
              <p className="text-[11px] text-ink-500">{loop.hop_count} hops</p>
            </div>
            <Badge tone="neutral" className={`${bg} ${text}`}>
              {(loop.risk || "low").toString().toUpperCase()}
            </Badge>
            <ChevronDown className={`h-4 w-4 text-ink-400 transition-transform ${open ? "rotate-180" : ""}`} />
          </div>
        </button>

        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} className="border-t border-ink-100 px-5 py-4">
            <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
              <LoopMiniGraph accounts={loop.accounts} />

              <div className="space-y-3">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-ink-700">
                  <ArrowRightLeft className="h-3.5 w-3.5 text-primary-500" /> Visual Flow
                </div>
                <p className="rounded-lg bg-bg-soft px-3 py-2 font-mono text-xs text-ink-700">
                  {loop.accounts.join(" → ")} → {loop.accounts[0]}
                </p>

                {loop.timeline && loop.timeline.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-ink-700">
                      <Clock className="h-3.5 w-3.5 text-primary-500" /> Timeline
                    </div>
                    <ul className="mt-1.5 space-y-1 text-xs text-ink-500">
                      {loop.timeline.map((t, i) => (
                        <li key={i}>• {t}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {loop.transactions && loop.transactions.length > 0 && (
              <div className="mt-5 overflow-x-auto rounded-xl border border-ink-100">
                <table className="w-full text-xs">
                  <thead className="bg-bg-soft text-ink-500">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Date</th>
                      <th className="px-3 py-2 text-left font-medium">Description</th>
                      <th className="px-3 py-2 text-right font-medium">Debit</th>
                      <th className="px-3 py-2 text-right font-medium">Credit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ink-100">
                    {loop.transactions.map((t, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 text-ink-700">{t.date}</td>
                        <td className="px-3 py-2 text-ink-700">{t.description}</td>
                        <td className="px-3 py-2 text-right text-danger">{t.debit ? formatINR(t.debit) : "—"}</td>
                        <td className="px-3 py-2 text-right text-success">{t.credit ? formatINR(t.credit) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </motion.div>
        )}
      </Card>
    </motion.div>
  );
}
