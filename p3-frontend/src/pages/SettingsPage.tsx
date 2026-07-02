import { useState } from "react";
import { Sun, Monitor, Bell, Download, Info } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { cn } from "../utils/cn";

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={cn("h-6 w-11 rounded-full transition-colors relative", checked ? "bg-primary-500" : "bg-ink-200")}
    >
      <span
        className={cn(
          "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
          checked ? "translate-x-5" : "translate-x-0.5"
        )}
      />
    </button>
  );
}

export function SettingsPage() {
  const [theme, setTheme] = useState<"light" | "system">("light");
  const [notifications, setNotifications] = useState({ alerts: true, weeklyDigest: false, riskEscalation: true });
  const [exportFormat, setExportFormat] = useState<"pdf" | "csv">("pdf");

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink-900">Settings</h1>
        <p className="text-sm text-ink-500">Manage your CipherTrail workspace preferences</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Theme</CardTitle>
          <CardDescription>Choose how CipherTrail looks on this device</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3">
          {[
            { key: "light", label: "Light", icon: Sun },
            { key: "system", label: "System", icon: Monitor },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setTheme(t.key as "light" | "system")}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border p-4 transition-colors",
                theme === t.key ? "border-primary-500 bg-primary-50" : "border-ink-100 hover:bg-bg-soft"
              )}
            >
              <t.icon className="h-5 w-5 text-ink-700" />
              <span className="text-xs font-medium text-ink-700">{t.label}</span>
            </button>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5"><Bell className="h-4 w-4" /> Notification Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            { key: "alerts", label: "Real-time risk alerts" },
            { key: "weeklyDigest", label: "Weekly investigation digest" },
            { key: "riskEscalation", label: "High-risk escalation emails" },
          ].map((n) => (
            <div key={n.key} className="flex items-center justify-between">
              <span className="text-sm text-ink-700">{n.label}</span>
              <Toggle
                checked={notifications[n.key as keyof typeof notifications]}
                onChange={(v) => setNotifications((s) => ({ ...s, [n.key]: v }))}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5"><Download className="h-4 w-4" /> Export Settings</CardTitle>
          <CardDescription>Default format for evidence report downloads</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-3">
          {(["pdf", "csv"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setExportFormat(f)}
              className={cn(
                "rounded-xl border px-4 py-2 text-xs font-semibold uppercase transition-colors",
                exportFormat === f ? "border-primary-500 bg-primary-50 text-primary-700" : "border-ink-100 text-ink-500 hover:bg-bg-soft"
              )}
            >
              {f}
            </button>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5"><Info className="h-4 w-4" /> About</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-ink-500 space-y-1">
          <p>CipherTrail · AI-Powered Financial Forensic Investigation Platform</p>
          <p>Built for the Karnataka CID Cyber Crime Investigation Unit</p>
          <p className="font-mono text-xs">v1.0.0</p>
        </CardContent>
      </Card>
    </div>
  );
}
