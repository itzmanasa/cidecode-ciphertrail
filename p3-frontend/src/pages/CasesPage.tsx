import { useNavigate } from "react-router-dom";
import { FolderOpen, FolderClock } from "lucide-react";
import { useCases } from "../hooks/useCases";
import { useCase } from "../context/CaseContext";
import { Card, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { DataTable, type Column } from "../components/ui/DataTable";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import type { CaseSummary } from "../types";
import { formatDate, formatNumber } from "../utils/format";

export function CasesPage() {
  const { data, isLoading } = useCases();
  const { setCaseId } = useCase();
  const navigate = useNavigate();

  const columns: Column<CaseSummary>[] = [
    { key: "case_id", header: "Case ID", sortValue: (r) => r.case_id, render: (r) => <span className="font-mono text-xs">{r.case_id}</span> },
    { key: "account_holder", header: "Account", sortValue: (r) => r.account_holder || "" },
    { key: "bank", header: "Bank", sortValue: (r) => r.bank || "" },
    { key: "upload_date", header: "Upload Date", sortValue: (r) => r.upload_date || "", render: (r) => formatDate(r.upload_date) },
    { key: "transactions", header: "Transactions", align: "right", sortValue: (r) => r.transactions || 0, render: (r) => formatNumber(r.transactions) },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    {
      key: "open",
      header: "",
      align: "right",
      render: (r) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            setCaseId(r.case_id);
            navigate("/dashboard");
          }}
        >
          <FolderOpen className="h-3.5 w-3.5" /> Open Investigation
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink-900">Uploaded Cases</h1>
        <p className="text-sm text-ink-500">All financial forensic investigations on record</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Case History</CardTitle>
          <CardDescription>Open any case to resume investigation</CardDescription>
        </CardHeader>
        <div className="px-5 pb-5">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="skeleton h-10 w-full" />
              ))}
            </div>
          ) : !data || data.length === 0 ? (
            <EmptyState
              icon={<FolderClock className="h-8 w-8" />}
              title="No cases uploaded yet"
              description="Upload a bank statement to begin your first investigation."
              action={<Button onClick={() => navigate("/upload")}>Upload statement</Button>}
            />
          ) : (
            <DataTable data={data} columns={columns} searchKeys={["case_id", "account_holder", "bank"]} pageSize={10} />
          )}
        </div>
      </Card>
    </div>
  );
}
