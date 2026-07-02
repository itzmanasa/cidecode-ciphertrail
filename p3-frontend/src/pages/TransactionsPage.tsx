import { useMemo } from "react";
import { Download, Receipt } from "lucide-react";
import { useCase } from "../context/CaseContext";
import { useTransactions } from "../hooks/useTransactions";
import { NoActiveCase } from "../components/layout/NoActiveCase";
import { Card, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { DataTable, type Column } from "../components/ui/DataTable";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import type { Transaction } from "../types";
import { formatINR, formatDate } from "../utils/format";

function toCSV(rows: Transaction[]): string {
  const headers = ["Date", "Description", "Debit", "Credit", "Balance", "Status", "Type", "Source", "Destination"];
  const lines = rows.map((r) =>
    [r.date, r.description, r.debit ?? "", r.credit ?? "", r.balance ?? "", r.status ?? "", r.transaction_type ?? "", r.source ?? "", r.destination ?? ""]
      .map((v) => `"${String(v).replace(/"/g, '""')}"`)
      .join(",")
  );
  return [headers.join(","), ...lines].join("\n");
}

export function TransactionsPage() {
  const { caseId } = useCase();
  const { data, isLoading } = useTransactions(caseId ?? undefined);

  const columns: Column<Transaction>[] = useMemo(
    () => [
      { key: "date", header: "Date", sortValue: (r) => r.date, render: (r) => formatDate(r.date) },
      { key: "description", header: "Description" },
      { key: "debit", header: "Debit", align: "right", sortValue: (r) => r.debit || 0, render: (r) => (r.debit ? formatINR(r.debit) : "—") },
      { key: "credit", header: "Credit", align: "right", sortValue: (r) => r.credit || 0, render: (r) => (r.credit ? formatINR(r.credit) : "—") },
      { key: "balance", header: "Balance", align: "right", sortValue: (r) => r.balance || 0, render: (r) => formatINR(r.balance) },
      { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
      { key: "transaction_type", header: "Type" },
      { key: "source", header: "Source" },
      { key: "destination", header: "Destination" },
    ],
    []
  );

  const handleExport = () => {
    if (!data) return;
    const blob = new Blob([toCSV(data)], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transactions_${caseId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!caseId) return <NoActiveCase />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-900">Transactions</h1>
          <p className="text-sm text-ink-500">Complete ledger for case <span className="font-mono">{caseId}</span></p>
        </div>
        <Button variant="outline" onClick={handleExport} disabled={!data || data.length === 0}>
          <Download className="h-4 w-4" /> Export CSV
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Transaction Ledger</CardTitle>
          <CardDescription>Search, sort, and filter every recorded transaction</CardDescription>
        </CardHeader>
        <div className="px-5 pb-5">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="skeleton h-10 w-full" />
              ))}
            </div>
          ) : !data || data.length === 0 ? (
            <EmptyState icon={<Receipt className="h-8 w-8" />} title="No transactions found" />
          ) : (
            <DataTable data={data} columns={columns} searchKeys={["description", "source", "destination"]} pageSize={12} />
          )}
        </div>
      </Card>
    </div>
  );
}
