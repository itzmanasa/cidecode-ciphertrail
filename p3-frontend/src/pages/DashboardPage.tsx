import {
  Activity,
  ArrowDownCircle,
  ArrowUpCircle,
  Scale,
  XCircle,
  RotateCcw,
  Banknote,
  FileSignature,
  Landmark,
  CheckCircle2,
} from "lucide-react";
import { useCase } from "../context/CaseContext";
import { useAnalysis } from "../hooks/useAnalysis";
import { IdentityCard } from "../components/dashboard/IdentityCard";
import { AIInsightPanel } from "../components/dashboard/AIInsightPanel";
import { DashboardCharts } from "../components/dashboard/DashboardCharts";
import { StatCard } from "../components/ui/StatCard";
import { NoActiveCase } from "../components/layout/NoActiveCase";
import { formatINR, formatNumber } from "../utils/format";

export function DashboardPage() {
  const { caseId } = useCase();
  const { data, isLoading, isError, error } = useAnalysis(caseId ?? undefined);

  if (!caseId) return <NoActiveCase />;

  const findings = data?.findings;
  const a = findings?.analytics;
  const identity = findings?.identity;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-900">Investigation Dashboard</h1>
          <p className="text-sm text-ink-500">Case ID: <span className="font-mono">{caseId}</span></p>
        </div>
      </div>

      {isError && (
        <div className="rounded-xl border border-danger/20 bg-danger-50 px-4 py-3 text-sm font-medium text-danger">
          {error instanceof Error ? error.message : "Failed to load analysis."}
        </div>
      )}

      <IdentityCard identity={identity} loading={isLoading} />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <StatCard label="Total Transactions" value={a?.total_transactions ?? 0} icon={<Activity className="h-4 w-4" />} delay={0.02} />
        <StatCard label="Total Debit" value={formatINR(a?.total_debit)} isString icon={<ArrowUpCircle className="h-4 w-4" />} tone="danger" delay={0.04} />
        <StatCard label="Total Credit" value={formatINR(a?.total_credit)} isString icon={<ArrowDownCircle className="h-4 w-4" />} tone="success" delay={0.06} />
        <StatCard label="Net Flow" value={formatINR(a?.net_flow)} isString icon={<Scale className="h-4 w-4" />} delay={0.08} />
        <StatCard label="Failed Transactions" value={a?.failed_transactions ?? 0} icon={<XCircle className="h-4 w-4" />} tone="danger" delay={0.1} />
        <StatCard label="Reversal Transactions" value={a?.reversal_transactions ?? 0} icon={<RotateCcw className="h-4 w-4" />} tone="warning" delay={0.12} />
        <StatCard label="Cash Withdrawals" value={formatNumber(a?.cash_withdrawals)} isString icon={<Banknote className="h-4 w-4" />} delay={0.14} />
        <StatCard label="Cheque Withdrawals" value={formatNumber(a?.cheque_withdrawals)} isString icon={<FileSignature className="h-4 w-4" />} delay={0.16} />
        <StatCard label="Unsourced Debits" value={formatNumber(a?.unsourced_debits)} isString icon={<Landmark className="h-4 w-4" />} tone="warning" delay={0.18} />
        <StatCard label="FIFO Status" value={a?.fifo_status ?? "—"} isString icon={<CheckCircle2 className="h-4 w-4" />} tone="success" delay={0.2} />
        <StatCard label="Balance Audit" value={a?.balance_audit_status ?? "—"} isString icon={<CheckCircle2 className="h-4 w-4" />} tone="success" delay={0.22} />
      </div>

      <AIInsightPanel brief={findings?.ai_brief} loading={isLoading} />

      <DashboardCharts analytics={a} />
    </div>
  );
}
