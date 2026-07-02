import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

interface CaseContextValue {
  caseId: string | null;
  setCaseId: (id: string | null) => void;
}

const CaseContext = createContext<CaseContextValue | undefined>(undefined);
const STORAGE_KEY = "ciphertrail:active_case_id";

export function CaseProvider({ children }: { children: ReactNode }) {
  const [caseId, setCaseIdState] = useState<string | null>(() =>
    typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null
  );

  useEffect(() => {
    if (caseId) window.localStorage.setItem(STORAGE_KEY, caseId);
    else window.localStorage.removeItem(STORAGE_KEY);
  }, [caseId]);

  const setCaseId = (id: string | null) => setCaseIdState(id);
  const value = useMemo(() => ({ caseId, setCaseId }), [caseId]);

  return <CaseContext.Provider value={value}>{children}</CaseContext.Provider>;
}

export function useCase() {
  const ctx = useContext(CaseContext);
  if (!ctx) throw new Error("useCase must be used within CaseProvider");
  return ctx;
}
