import { useMemo } from "react";
import { Repeat, RefreshCw, AlertOctagon, Maximize2 } from "lucide-react";
import { useCase } from "../context/CaseContext";
import { useAnalysis } from "../hooks/useAnalysis";
import { NoActiveCase } from "../components/layout/NoActiveCase";
import { StatCard } from "../components/ui/StatCard";
import { RoundTripCard } from "../components/roundtrip/RoundTripCard";
import { EmptyState } from "../components/ui/EmptyState";
import { formatINR } from "../utils/format";

export function RoundTrippingPage() {
  const { caseId } = useCase();
  const { data, isLoading } = useAnalysis(caseId ?? undefined);

  const loops = data?.findings?.round_trips ?? [];

  const stats = useMemo(() => {
    const moneyCycled = loops.reduce((sum, l) => sum + (l.amount || 0), 0);
    const highestRisk = [...loops].sort((a, b) => {
      const order: Record<string, number> = { high: 3, critical: 4, medium: 2, low: 1 };
      return (order[(b.risk || "low").toLowerCase()] || 0) - (order[(a.risk || "low").toLowerCase()] || 0);
    })[0];
    const largest = [...loops].sort((a, b) => (b.amount || 0) - (a.amount || 0))[0];
    return { moneyCycled, highestRisk, largest };
  }, [loops]);

  if (!caseId) return <NoActiveCase />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink-900">Round Tripping</h1>
        <p className="text-sm text-ink-500">Circular fund-transfer detection across linked accounts</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Loops Found" value={loops.length} icon={<Repeat className="h-4 w-4" />} />
        <StatCard label="Money Cycled" value={formatINR(stats.moneyCycled)} isString icon={<RefreshCw className="h-4 w-4" />} tone="warning" />
        <StatCard
          label="Highest Risk Ring"
          value={stats.highestRisk ? stats.highestRisk.loop_id : "—"}
          isString
          icon={<AlertOctagon className="h-4 w-4" />}
          tone="danger"
        />
        <StatCard
          label="Largest Loop"
          value={stats.largest ? formatINR(stats.largest.amount) : "—"}
          isString
          icon={<Maximize2 className="h-4 w-4" />}
        />
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton h-16 w-full" />
          ))}
        </div>
      ) : loops.length === 0 ? (
        <EmptyState
          icon={<Repeat className="h-8 w-8" />}
          title="No round-tripping loops detected"
          description="No circular fund movement was found across the accounts in this case."
        />
      ) : (
        <div className="space-y-3">
          {loops.map((loop, i) => (
            <RoundTripCard key={loop.loop_id} loop={loop} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
