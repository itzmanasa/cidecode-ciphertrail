import { useState } from "react";
import { FileDown, ShieldCheck, FileText, Repeat, Sparkles, ListChecks } from "lucide-react";
import { useCase } from "../context/CaseContext";
import { useAnalysis } from "../hooks/useAnalysis";
import { NoActiveCase } from "../components/layout/NoActiveCase";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { generateEvidenceReport } from "../services/reportGenerator";
import { formatINR, formatDate, truncateMiddle } from "../utils/format";

const SECTIONS = [
  { key: "identity", label: "Identity", icon: ShieldCheck },
  { key: "analytics", label: "Analytics", icon: ListChecks },
  { key: "roundtrips", label: "Round Trips", icon: Repeat },
  { key: "ai", label: "AI Summary", icon: Sparkles },
  { key: "audit", label: "Audit Results", icon: FileText },
];

export function EvidenceReportPage() {
  const { caseId } = useCase();
  const { data, isLoading } = useAnalysis(caseId ?? undefined);
  const [generating, setGenerating] = useState(false);

  if (!caseId) return <NoActiveCase />;

  const f = data?.findings;
  const identity = f?.identity;
  const a = f?.analytics;

  const handleGenerate = async () => {
    if (!data) return;
    setGenerating(true);
    try {
      generateEvidenceReport(data);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-900">Evidence Report</h1>
          <p className="text-sm text-ink-500">Section 65B-certified investigation report for case <span className="font-mono">{caseId}</span></p>
        </div>
        <Button onClick={handleGenerate} disabled={isLoading || !data || generating}>
          <FileDown className="h-4 w-4" /> {generating ? "Generating…" : "Generate PDF Report"}
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {SECTIONS.map((s) => (
          <Badge key={s.key} tone="primary" className="px-3 py-1.5">
            <s.icon className="h-3 w-3" /> {s.label}
          </Badge>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5"><ShieldCheck className="h-4 w-4 text-primary-500" /> Identity</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {[
            ["Account Holder", identity?.account_holder],
            ["Bank", identity?.bank],
            ["IFSC", identity?.ifsc],
            ["Investigation ID", identity?.investigation_id || caseId],
            ["Upload Time", formatDate(identity?.upload_time)],
            ["SHA256", identity?.sha256 ? truncateMiddle(identity.sha256 as string, 10, 8) : "—"],
          ].map(([label, value]) => (
            <div key={label as string}>
              <p className="text-[11px] font-medium text-ink-500">{label}</p>
              <p className="mt-0.5 truncate text-sm font-semibold text-ink-900">{(value as string) || "—"}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5"><ListChecks className="h-4 w-4 text-primary-500" /> Analytics</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            ["Total Transactions", a?.total_transactions],
            ["Total Debit", formatINR(a?.total_debit)],
            ["Total Credit", formatINR(a?.total_credit)],
            ["Net Flow", formatINR(a?.net_flow)],
          ].map(([label, value]) => (
            <div key={label as string}>
              <p className="text-[11px] font-medium text-ink-500">{label}</p>
              <p className="mt-0.5 text-sm font-bold text-ink-900">{value ?? "—"}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5"><Repeat className="h-4 w-4 text-primary-500" /> Round Trips</CardTitle>
          <CardDescription>{f?.round_trips?.length ?? 0} loop(s) detected</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {(f?.round_trips ?? []).slice(0, 4).map((l) => (
            <div key={l.loop_id} className="flex items-center justify-between rounded-lg border border-ink-100 px-3 py-2 text-xs">
              <span className="font-medium text-ink-700">Loop {l.loop_id}</span>
              <span className="text-ink-500">{formatINR(l.amount)}</span>
            </div>
          ))}
          {(!f?.round_trips || f.round_trips.length === 0) && (
            <p className="text-xs text-ink-500">No round-tripping loops detected.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5"><Sparkles className="h-4 w-4 text-primary-500" /> AI Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-line text-sm text-ink-700">
            {typeof f?.ai_brief === "string" ? f?.ai_brief : f?.ai_brief?.risk_summary || "No AI brief available."}
          </p>
        </CardContent>
      </Card>

      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>Digital Signature Area</CardTitle>
          <CardDescription>Embedded automatically into the generated PDF</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-4">
          <div><p className="font-medium text-ink-500">SHA256</p><p className="font-mono text-ink-700">{identity?.sha256 ? truncateMiddle(identity.sha256 as string, 8, 6) : "—"}</p></div>
          <div><p className="font-medium text-ink-500">MD5</p><p className="font-mono text-ink-700">{identity?.md5 || "—"}</p></div>
          <div><p className="font-medium text-ink-500">UTC Timestamp</p><p className="font-mono text-ink-700">{new Date().toISOString().slice(0, 19)}Z</p></div>
          <div><p className="font-medium text-ink-500">Investigation ID</p><p className="font-mono text-ink-700">{identity?.investigation_id || caseId}</p></div>
        </CardContent>
      </Card>
    </div>
  );
}
