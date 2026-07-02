import { motion } from "framer-motion";
import { Sparkles, AlertTriangle, Users, ListChecks } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "../ui/Card";
import type { AIBrief } from "../../types";

function Section({ icon: Icon, title, children }: { icon: typeof Sparkles; title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-xs font-semibold text-ink-700">
        <Icon className="h-3.5 w-3.5 text-primary-500" /> {title}
      </div>
      <div className="mt-2">{children}</div>
    </div>
  );
}

export function AIInsightPanel({ brief, loading }: { brief?: string | AIBrief; loading?: boolean }) {
  if (loading) {
    return (
      <Card className="p-6">
        <div className="skeleton h-5 w-40 mb-4" />
        <div className="skeleton h-24 w-full" />
      </Card>
    );
  }

  const isStructured = typeof brief === "object" && brief !== null;
  const text = !isStructured ? (brief as string | undefined) : undefined;
  const structured = isStructured ? (brief as AIBrief) : undefined;

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-center gap-3 border-b border-ink-100 pb-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-grad-primary text-white shadow-glow">
          <Sparkles className="h-4 w-4" />
        </div>
        <div>
          <CardTitle>AI Investigation Summary</CardTitle>
          <CardDescription>Generated from transaction-level forensic analysis</CardDescription>
        </div>
      </CardHeader>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4 }}
        className="space-y-5 px-6 py-5"
      >
        {text && (
          <p className="whitespace-pre-line text-sm leading-relaxed text-ink-700">{text}</p>
        )}

        {structured?.risk_summary && (
          <Section icon={AlertTriangle} title="Risk Summary">
            <p className="rounded-xl bg-warning-50 px-3 py-2 text-sm text-ink-700">{structured.risk_summary}</p>
          </Section>
        )}

        {structured?.key_findings && structured.key_findings.length > 0 && (
          <Section icon={ListChecks} title="Key Findings">
            <ul className="space-y-1.5">
              {structured.key_findings.map((k, i) => (
                <li key={i} className="flex gap-2 text-sm text-ink-700">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary-500" />
                  {k}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {structured?.important_entities && structured.important_entities.length > 0 && (
          <Section icon={Users} title="Important Entities">
            <div className="flex flex-wrap gap-1.5">
              {structured.important_entities.map((e, i) => (
                <span key={i} className="rounded-full bg-primary-50 px-2.5 py-1 text-xs font-medium text-primary-700">
                  {e}
                </span>
              ))}
            </div>
          </Section>
        )}

        {structured?.recommendations && structured.recommendations.length > 0 && (
          <Section icon={ListChecks} title="Recommendations">
            <ul className="space-y-1.5">
              {structured.recommendations.map((r, i) => (
                <li key={i} className="flex gap-2 text-sm text-ink-700">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-secondary-500" />
                  {r}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {!text && !structured && (
          <p className="text-sm text-ink-500">AI brief not available for this case yet.</p>
        )}
      </motion.div>
    </Card>
  );
}
