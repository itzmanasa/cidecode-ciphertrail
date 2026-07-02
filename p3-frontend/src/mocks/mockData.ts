import type {
  UploadResponse,
  AnalyseResponse,
  Transaction,
  CaseSummary,
  CleanResponse,
} from "../types";
import { generateFindings, generateCaseSummary, generateTransactions } from "./generator";

const STORE_KEY = "ciphertrail:mock_cases";

function seedDefaultCases(): CaseSummary[] {
  return [
    { case_id: "CASE-2025-00812", account_holder: "Ramesh Kumar", bank: "State Bank of India", upload_date: new Date(Date.now() - 86400000 * 6).toISOString(), transactions: 61, status: "Processed" },
    { case_id: "CASE-2025-00915", account_holder: "Anita Rao", bank: "HDFC Bank", upload_date: new Date(Date.now() - 86400000 * 2).toISOString(), transactions: 54, status: "Processed" },
  ];
}

function readStore(): CaseSummary[] {
  try {
    const raw = window.localStorage.getItem(STORE_KEY);
    if (!raw) {
      const seeded = seedDefaultCases();
      window.localStorage.setItem(STORE_KEY, JSON.stringify(seeded));
      return seeded;
    }
    return JSON.parse(raw) as CaseSummary[];
  } catch {
    return seedDefaultCases();
  }
}

function writeStore(cases: CaseSummary[]) {
  try {
    window.localStorage.setItem(STORE_KEY, JSON.stringify(cases));
  } catch {
    // localStorage unavailable — mock data will still work for this session
  }
}

function delay<T>(value: T, ms = 500): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export async function mockFetchCases(): Promise<CaseSummary[]> {
  return delay(readStore(), 350);
}

export async function mockUploadStatement(
  file: File,
  onProgress?: (pct: number) => void
): Promise<UploadResponse> {
  // Simulate a realistic progress bar while there's no real network transfer.
  if (onProgress) {
    for (const pct of [15, 35, 55, 75, 92, 100]) {
      await delay(null, 140);
      onProgress(pct);
    }
  } else {
    await delay(null, 800);
  }

  const caseId = `CASE-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 90000) + 10000)}`;
  const summary = generateCaseSummary(caseId);
  const cases = readStore();
  cases.unshift({ ...summary, account_holder: summary.account_holder ?? file.name });
  writeStore(cases);

  return { case_id: caseId };
}

export async function mockFetchAnalysis(caseId: string): Promise<AnalyseResponse> {
  const findings = generateFindings(caseId, caseId);
  return delay({ case_id: caseId, findings }, 600);
}

export async function mockFetchTransactions(caseId: string): Promise<Transaction[]> {
  return delay(generateTransactions(caseId), 450);
}

export async function mockCleanStatement(file: File): Promise<CleanResponse> {
  const txns = generateTransactions(file.name || "clean-upload");
  return delay(
    {
      success: true,
      statement: {
        account_holder: "Unknown",
        transactions: txns,
      },
      audit_results: { balance_audit_status: "Matched", fifo_status: "Consistent" },
      summary_stats: { total_transactions: txns.length },
    },
    600
  );
}
