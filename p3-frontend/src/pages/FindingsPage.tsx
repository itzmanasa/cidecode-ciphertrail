import { useState } from "react";
import {
  XCircle,
  RotateCcw,
  Zap,
  Users,
  Smartphone,
  ShieldAlert,
  Bell,
} from "lucide-react";
import { useCase } from "../context/CaseContext";
import { useAnalysis } from "../hooks/useAnalysis";
import { NoActiveCase } from "../components/layout/NoActiveCase";
import { Card, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { DataTable, type Column } from "../components/ui/DataTable";
import { StatusBadge } from "../components/ui/StatusBadge";
import { EmptyState } from "../components/ui/EmptyState";
import type { Transaction, AlertItem } from "../types";
import { formatINR, formatDate } from "../utils/format";
import { cn } from "../utils/cn";

const TABS = [
  { key: "failed", label: "Failed Transactions", icon: XCircle },
  { key: "reversal", label: "Reversal Transactions", icon: RotateCcw },
  { key: "velocity", label: "Velocity Anomalies", icon: Zap },
  { key: "upi", label: "Most Active UPI IDs", icon: Smartphone },
  { key: "accounts", label: "Most Active Accounts", icon: Users },
  { key: "risk", label: "Highest Risk Accounts", icon: ShieldAlert },
];

const txnColumns: Column<Transaction>[] = [
  { key: "date", header: "Date", sortValue: (r) => r.date, render: (r) => formatDate(r.date) },
  { key: "description", header: "Description" },
  { key: "debit", header: "Debit", align: "right", sortValue: (r) => r.debit || 0, render: (r) => (r.debit ? formatINR(r.debit) : "—") },
  { key: "credit", header: "Credit", align: "right", sortValue: (r) => r.credit || 0, render: (r) => (r.credit ? formatINR(r.credit) : "—") },
  { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
];

function GenericList({ items }: { items: unknown[] }) {
  if (!items || items.length === 0) {
    return <EmptyState icon={<Users className="h-7 w-7" />} title="No records found" />;
  }
  return (
    <div className="divide-y divide-ink-100">
      {items.map((item, i) => (
        <div key={i} className="flex items-center justify-between py-2.5 text-sm">
          <span className="font-mono text-xs text-ink-700">
            {typeof item === "string" ? item : JSON.stringify(item)}
          </span>
        </div>
      ))}
    </div>
  );
}

function AlertsFeed({ alerts }: { alerts?: AlertItem[] }) {
  if (!alerts || alerts.length === 0) {
    return <EmptyState icon={<Bell className="h-7 w-7" />} title="No active alerts" />;
  }
  return (
    <div className="space-y-2.5">
      {alerts.map((a) => (
        <div key={a.id} className="flex items-start gap-3 rounded-xl border border-ink-100 px-3 py-2.5">
          <span className="mt-0.5">
            <StatusBadge status={a.severity} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-ink-900">{a.title}</p>
            {a.description && <p className="text-xs text-ink-500">{a.description}</p>}
          </div>
          {a.timestamp && <span className="shrink-0 text-[11px] text-ink-400">{formatDate(a.timestamp)}</span>}
        </div>
      ))}
    </div>
  );
}

export function FindingsPage() {
  const { caseId } = useCase();
  const { data, isLoading } = useAnalysis(caseId ?? undefined);
  const [tab, setTab] = useState("failed");

  if (!caseId) return <NoActiveCase />;

  const f = data?.findings;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink-900">Investigation Findings</h1>
        <p className="text-sm text-ink-500">Detailed forensic breakdown of anomalies and entities</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Alerts Feed</CardTitle>
          <CardDescription>Real-time risk alerts generated for this case</CardDescription>
        </CardHeader>
        <div className="px-5 pb-5">
          {isLoading ? <div className="skeleton h-20 w-full" /> : <AlertsFeed alerts={f?.alerts} />}
        </div>
      </Card>

      <Card>
        <div className="flex flex-wrap gap-1 border-b border-ink-100 px-3 pt-3">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={cn(
                "flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-xs font-medium transition-colors",
                tab === t.key ? "bg-primary-50 text-primary-700" : "text-ink-500 hover:text-ink-700"
              )}
            >
              <t.icon className="h-3.5 w-3.5" /> {t.label}
            </button>
          ))}
        </div>

        <div className="p-5">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="skeleton h-10 w-full" />
              ))}
            </div>
          ) : tab === "failed" ? (
            <DataTable data={f?.failed_transactions ?? []} columns={txnColumns} searchKeys={["description"]} />
          ) : tab === "reversal" ? (
            <DataTable data={f?.reversal_transactions ?? []} columns={txnColumns} searchKeys={["description"]} />
          ) : tab === "velocity" ? (
            <GenericList items={f?.velocity_anomalies ?? []} />
          ) : tab === "upi" ? (
            <GenericList items={f?.most_active_upi ?? []} />
          ) : tab === "accounts" ? (
            <GenericList items={f?.most_active_accounts ?? []} />
          ) : (
            <GenericList items={f?.highest_risk_accounts ?? []} />
          )}
        </div>
      </Card>
    </div>
  );
}
