import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Skeleton } from "../ui/Skeleton";
import type { IdentityInfo } from "../../types";
import { formatDate, truncateMiddle } from "../../utils/format";
import { Landmark, Hash, Fingerprint, Mail, Building2, ShieldCheck } from "lucide-react";

const FIELDS: { key: keyof IdentityInfo; label: string; icon: typeof Landmark }[] = [
  { key: "account_holder", label: "Account Holder", icon: Landmark },
  { key: "account_number", label: "Account Number", icon: Hash },
  { key: "bank", label: "Bank", icon: Building2 },
  { key: "branch", label: "Branch", icon: Building2 },
  { key: "ifsc", label: "IFSC", icon: Hash },
  { key: "email", label: "Email", icon: Mail },
  { key: "investigation_id", label: "Investigation ID", icon: Fingerprint },
];

export function IdentityCard({ identity, loading }: { identity?: IdentityInfo; loading?: boolean }) {
  if (loading) {
    return (
      <Card className="p-6">
        <Skeleton className="h-5 w-48 mb-4" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Array.from({ length: 7 }).map((_, i) => (
            <Skeleton key={i} className="h-10" />
          ))}
        </div>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="bg-grad-primary px-6 py-5 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-white/70">Account Under Investigation</p>
            <h2 className="mt-0.5 text-xl font-bold">{identity?.account_holder || "Unidentified Holder"}</h2>
          </div>
          <Badge tone="neutral" className="bg-white/15 text-white ring-white/20">
            <ShieldCheck className="h-3 w-3" /> Verified intake
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-5 px-6 py-5 sm:grid-cols-4">
        {FIELDS.map((f) => (
          <div key={f.key} className="min-w-0">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-ink-500">
              <f.icon className="h-3 w-3" /> {f.label}
            </div>
            <p className="mt-1 truncate text-sm font-semibold text-ink-900">
              {(identity?.[f.key] as string) || "—"}
            </p>
          </div>
        ))}
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-ink-500">
            <Fingerprint className="h-3 w-3" /> Upload Time
          </div>
          <p className="mt-1 truncate text-sm font-semibold text-ink-900">{formatDate(identity?.upload_time)}</p>
        </div>
      </div>

      {identity?.sha256 && (
        <div className="border-t border-ink-100 bg-bg-soft px-6 py-3">
          <p className="text-[11px] font-medium text-ink-500">SHA256 Hash</p>
          <p className="mt-0.5 font-mono text-xs text-ink-700" title={identity.sha256 as string}>
            {truncateMiddle(identity.sha256 as string, 24, 16)}
          </p>
        </div>
      )}
    </Card>
  );
}
