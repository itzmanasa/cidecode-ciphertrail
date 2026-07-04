import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Clock, ShieldCheck, FileSearch, LogOut, WifiOff } from "lucide-react";
import { Dropzone } from "../components/upload/Dropzone";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { uploadMultipleStatements } from "../api/endpoints";
import { useCase } from "../context/CaseContext";
import { useCases } from "../hooks/useCases";
import { useAuth } from "../context/AuthContext";
import { getMockMode, subscribeMockMode } from "../lib/mockMode";
import { formatDate } from "../utils/format";

export function UploadPage() {
  const navigate = useNavigate();
  const { setCaseId } = useCase();
  const { user, logout } = useAuth();
  const [progress, setProgress] = useState(0);
  const [mockMode, setMockModeState] = useState(getMockMode());
  const { data: cases, isLoading: casesLoading } = useCases();

  useEffect(() => subscribeMockMode(setMockModeState), []);

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const mutation = useMutation({
    mutationFn: (files: File[]) => uploadMultipleStatements(files, setProgress),
    onSuccess: (data) => {
      setCaseId(data.case_id);
      navigate("/dashboard");
    },
  });

  return (
    <div className="mx-auto max-w-4xl space-y-8 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-grad-primary text-white shadow-glow">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <p className="text-sm font-bold text-ink-900">CipherTrail</p>
        </div>
        <div className="flex items-center gap-3">
          {mockMode && (
            <span className="hidden sm:flex items-center gap-1.5 rounded-lg bg-warning-50 px-2.5 py-1.5 text-[11px] font-semibold text-warning ring-1 ring-warning/15">
              <WifiOff className="h-3.5 w-3.5" /> Offline demo data
            </span>
          )}
          <span className="hidden sm:block text-xs font-medium text-ink-500">{user?.name}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 rounded-xl border border-ink-100 bg-white px-3 py-1.5 text-xs font-medium text-ink-700 hover:bg-ink-100/50 transition-colors"
          >
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </button>
        </div>
      </div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-center">
        <Badge tone="primary" className="mb-3">Karnataka CID · Cyber Crime Investigation Unit</Badge>
        <h1 className="text-3xl font-bold tracking-tight text-ink-900">
          Begin a new financial forensic investigation
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-sm text-ink-500">
          Upload a bank statement to automatically trace money flow, detect round-tripping,
          and generate an AI-assisted investigation brief.
        </p>
      </motion.div>

      <Dropzone
        onFilesSelected={(files) => {
          setProgress(0);
          mutation.mutate(files);
        }}
        uploading={mutation.isPending}
        progress={progress}
      />

      {mutation.isError && (
        <p className="text-center text-sm font-medium text-danger">
          {mutation.error instanceof Error ? mutation.error.message : "Upload failed."}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { icon: ShieldCheck, title: "Tamper-evident", desc: "SHA256 hashed on ingest for Section 65B evidence." },
          { icon: FileSearch, title: "AI-assisted", desc: "Automated round-trip and anomaly detection." },
          { icon: Clock, title: "Fast triage", desc: "Full investigation brief generated in seconds." },
        ].map((f) => (
          <Card key={f.title} className="p-4">
            <f.icon className="h-5 w-5 text-primary-500" />
            <p className="mt-2 text-sm font-semibold text-ink-900">{f.title}</p>
            <p className="text-xs text-ink-500">{f.desc}</p>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent investigations</CardTitle>
          <CardDescription>Previously uploaded cases and statements</CardDescription>
        </CardHeader>
        <CardContent>
          {casesLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="skeleton h-12 w-full" />
              ))}
            </div>
          ) : !cases || cases.length === 0 ? (
            <EmptyState
              icon={<FileSearch className="h-8 w-8" />}
              title="No uploads yet"
              description="Once you upload a statement, it will appear here for quick access."
            />
          ) : (
            <div className="divide-y divide-ink-100">
              {cases.slice(0, 5).map((c) => (
                <button
                  key={c.case_id}
                  onClick={() => {
                    setCaseId(c.case_id);
                    navigate("/dashboard");
                  }}
                  className="flex w-full items-center justify-between gap-3 py-3 text-left hover:bg-bg-soft/60 rounded-lg px-2 -mx-2 transition-colors"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink-900">
                      {c.account_holder || c.case_id}
                    </p>
                    <p className="text-xs text-ink-500">{c.bank || "Unknown bank"} · {formatDate(c.upload_date)}</p>
                  </div>
                  <Badge tone="neutral">{c.status || "Processed"}</Badge>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
