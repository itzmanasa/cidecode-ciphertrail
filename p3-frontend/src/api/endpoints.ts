import { apiClient, ApiError } from "./client";
import type {
  UploadResponse,
  AnalyseResponse,
  Transaction,
  CaseSummary,
  CleanResponse,
} from "../types";
import {
  mockFetchCases,
  mockUploadStatement,
  mockFetchAnalysis,
  mockFetchTransactions,
  mockCleanStatement,
} from "../mocks/mockData";
import { setMockMode } from "../lib/mockMode";
import { shouldSkipBackend, markBackendOffline, markBackendOnline } from "./backendStatus";

function buildChartData(transactions: any[]) {
  const dailyMap: Record<string, { count: number; debit: number; credit: number }> = {};
  const typeMap: Record<string, number> = {};
  let cashTotal = 0, digitalTotal = 0, cumulative = 0;
  const timelineMap: Record<string, number> = {};

  for (const t of transactions) {
    const date = (t.date ?? "").slice(0, 10);
    if (!date) continue;

    // daily counts + debit/credit
    if (!dailyMap[date]) dailyMap[date] = { count: 0, debit: 0, credit: 0 };
    dailyMap[date].count++;
    dailyMap[date].debit  += t.debit  ?? 0;
    dailyMap[date].credit += t.credit ?? 0;

    // transaction types (mode)
    const narration = (t.narration ?? t.particulars ?? "").toUpperCase();
  const fromAcc   = (t.from_account ?? "").toUpperCase();
  const toAcc     = (t.to_account   ?? "").toUpperCase();

  const mode =
    narration.includes("UPI")  || fromAcc.includes("UPI")  ? "UPI"  :
    narration.includes("NEFT") || fromAcc.includes("NEFT") || toAcc.includes("NEFT") ? "NEFT" :
    narration.includes("RTGS") || fromAcc.includes("RTGS") || toAcc.includes("RTGS") ? "RTGS" :
    narration.includes("IMPS") || fromAcc.includes("IMPS") || toAcc.includes("IMPS") ? "IMPS" :
    narration.includes("ATM")  || toAcc.includes("ATM")    ? "CASH_WITHDRAWAL" :
    narration.includes("CASH") || fromAcc.includes("CASH") ? "CASH_DEPOSIT" :
    narration.includes("CHQ")  || narration.includes("CHEQUE") ? "CHEQUE" :
    t.txn_type ?? "OTHER";

  typeMap[mode] = (typeMap[mode] ?? 0) + 1;

  const isCash = mode === "CASH_WITHDRAWAL" || mode === "CASH_DEPOSIT";
    const amount = (t.debit ?? 0) + (t.credit ?? 0);
    if (isCash) cashTotal += amount;
    else digitalTotal += amount;

    // cumulative timeline
    cumulative += (t.debit ?? 0) + (t.credit ?? 0);
    timelineMap[date] = cumulative;
  }

  const sorted = Object.keys(dailyMap).sort();

  return {
    daily_transactions: sorted.map((d) => ({ date: d, count: dailyMap[d].count })),
    debit_vs_credit:    sorted.map((d) => ({ date: d, debit: dailyMap[d].debit, credit: dailyMap[d].credit })),
    transaction_types:  Object.entries(typeMap).map(([type, value]) => ({ type, value })),
    cash_vs_digital: [
      { name: "Cash",    value: Math.round(cashTotal) },
      { name: "Digital", value: Math.round(digitalTotal) },
    ],
    timeline: sorted.map((d) => ({ date: d, value: Math.round(timelineMap[d]) })),
  };
}
// Normalises P2's response shapes into what the UI components expect.
// P2 splits identity fields across /upload and /analyse — we merge them here.
function normaliseAnalysis(raw: any, uploadMeta?: any): AnalyseResponse {
  const f = raw.findings ?? {};
  const a = f.analytics ?? {};
  const audit = uploadMeta?.audit ?? {};

  const total_debit   = audit.total_debit   !== undefined ? audit.total_debit   : (a.total_debit   ?? 0);
  const total_credit  = audit.total_credit  !== undefined ? audit.total_credit  : (a.total_credit  ?? 0);

  return {
    ...raw,
    findings: {
      ...f,
      analytics: {
        total_transactions:   a.total_transactions   ?? 0,
        clean_transactions:   a.clean_transactions   ?? 0,
        total_debit,
        total_credit,
        net_flow:             total_credit - total_debit,
        failed_transactions:  a.failed_transactions  ?? 0,
        reversal_transactions: a.reversal_count      ?? a.reversal_transactions ?? 0,
        reversal_amount:      a.reversal_amount      ?? 0,
        cash_withdrawals:     audit.cash_withdrawal_count  ?? a.cash_withdrawals ?? 0,
        cheque_withdrawals:   audit.cheque_withdrawal_count ?? a.cheque_withdrawals ?? 0,
        cash_withdrawal_total:   audit.cash_withdrawal_total  ?? 0,
        cheque_withdrawal_total: audit.cheque_withdrawal_total ?? 0,
        unsourced_debits:     a.unsourced_debits ?? 0,
        fifo_status:          a.fifo_status ?? (audit.balance_audit_clean ? "Clean" : "Review"),
        balance_audit_status: audit.balance_audit_clean === true  ? "Clean" :
                              audit.balance_audit_clean === false ? "Mismatch" : "—",
        total_amount_moved:   a.total_amount_moved ?? total_debit,
        daily_transactions:   a.daily_transactions  ?? [],
        debit_vs_credit:      a.debit_vs_credit     ?? [],
        transaction_types:    a.transaction_types   ?? [],
        cash_vs_digital:      a.cash_vs_digital     ?? [],
        timeline:             a.timeline            ?? [],
      },
      identity: {
        account_number:   uploadMeta?.account_id   ?? f.identity?.account_number ?? null,
        account_holder:   uploadMeta?.owner_name   ?? f.identity?.account_holder ?? null,
        bank:             uploadMeta?.bank_name    ?? f.identity?.bank           ?? null,
        bank_name:        uploadMeta?.bank_name    ?? f.identity?.bank_name      ?? null,
        owner_name:       uploadMeta?.owner_name   ?? f.identity?.owner_name     ?? null,
        branch:           f.identity?.branch       ?? uploadMeta?.branch         ?? null,
        ifsc:             f.identity?.ifsc         ?? uploadMeta?.ifsc           ?? null,
        email:            f.identity?.email        ?? uploadMeta?.email          ?? null,
        period_from:      uploadMeta?.period_from  ?? f.identity?.period_from    ?? null,
        period_to:        uploadMeta?.period_to    ?? f.identity?.period_to      ?? null,
        sha256:           uploadMeta?.file_hash    ?? f.identity?.sha256         ?? null,
        investigation_id: uploadMeta?.case_id      ?? null,
        upload_time:      uploadMeta?.upload_time  ?? new Date().toISOString(),
      }, // matches IdentityInfo type
  
      round_trips: (f.round_trips ?? []).map((rt: any, i: number) => ({
        ...rt,
        loop_id:      rt.loop_id        ?? rt.id             ?? `LOOP_${i + 1}`,
        accounts: rt.accounts ?? rt.nodes ?? rt.path ?? 
          (rt.cycle_str ? rt.cycle_str.replace(/ /g, "").split("→") : 
          (rt.chain ? rt.chain.replace(/ /g, "").split("→") : [])),        amount:       rt.amount         ?? rt.total_amount   ?? 0,
        hop_count:    rt.hop_count      ?? rt.hops           ?? (rt.accounts ?? rt.nodes ?? rt.path ?? []).length,
        risk:         (rt.risk          ?? "high").toLowerCase(),
        timeline:     rt.timeline       ?? [],
        transactions: rt.transactions   ?? [],
      })),
      high_risk_accounts: f.high_risk_accounts ?? [],
      suspicious_nodes:   f.suspicious_nodes   ?? {},
      graph: f.graph ? {
        nodes: (f.graph.nodes ?? []).map((n: any) => ({
          ...n,
          id:      n.id ?? n.account_number ?? String(Math.random()),
          label:   n.label ?? n.id ?? n.account_number ?? "Account",
          risk:    (n.risk ?? "low").toLowerCase(),
          account: n.id ?? n.account_number,
        })),
        edges: (f.graph.edges ?? []).map((e: any, i: number) => ({
          ...e,
          id:     e.id ?? `e-${i}`,
          source: e.source ?? e.from,   // ← P2 sends "from", ReactFlow needs "source"
          target: e.target ?? e.to,     // ← P2 sends "to",   ReactFlow needs "target"
          amount: e.amount ?? 0,
          risk:   (e.risk ?? "low").toLowerCase(),
          label:  e.label ?? null,
        })),
      } : { nodes: [], edges: [] },
      ai_brief:           f.ai_brief           ?? null,
    },
  };
}

function isNetworkError(err: unknown): boolean {
  return err instanceof ApiError && err.isNetworkError;
}
const _uploadCache: Record<string, UploadResponse> = {};
export async function uploadStatement(
  file: File,
  onProgress?: (pct: number) => void
): Promise<UploadResponse> {
  if (shouldSkipBackend()) {
    setMockMode(true);
    const result = await mockUploadStatement(file, onProgress);
    _uploadCache[result.case_id] = result;
    return result;
  }

  try {
    const formData = new FormData();
    formData.append("file", file);

    const { data } = await apiClient.post<UploadResponse>("/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      // Real statement processing can legitimately take longer than a plain
      // GET, so this call gets more room than the 8s default — but a dead
      // backend still fails via ECONNREFUSED almost immediately either way.
      timeout: 45000,
      onUploadProgress: (evt) => {
        if (onProgress && evt.total) {
          onProgress(Math.round((evt.loaded / evt.total) * 100));
        }
      },
    });
    markBackendOnline();
    _uploadCache[data.case_id] = data
    setMockMode(false);
    return data;
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      const result = await mockUploadStatement(file, onProgress);
      _uploadCache[result.case_id] = result;
      return result;
    }
    throw err;
  }
}

export async function uploadMultipleStatements(
  files: File[],
  onProgress?: (pct: number) => void
): Promise<UploadResponse> {
  if (files.length === 1) return uploadStatement(files[0], onProgress);

  if (shouldSkipBackend()) {
    setMockMode(true);
    const result = await mockUploadStatement(files[0], onProgress);
    _uploadCache[result.case_id] = result;
    return result;
  }

  try {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));

    const { data } = await apiClient.post<UploadResponse>("/upload-multi", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000,
      onUploadProgress: (evt) => {
        if (onProgress && evt.total)
          onProgress(Math.round((evt.loaded / evt.total) * 100));
      },
    });
    markBackendOnline();
    setMockMode(false);
    _uploadCache[data.case_id] = data;
    return data;
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      const result = await mockUploadStatement(files[0], onProgress);
      _uploadCache[result.case_id] = result;
      return result;
    }
    throw err;
  }
}

export async function fetchAnalysis(caseId: string): Promise<AnalyseResponse> {
  if (shouldSkipBackend()) {
    setMockMode(true);
    return normaliseAnalysis(await mockFetchAnalysis(caseId), _uploadCache[caseId]);
  }

  try {
    const [{ data }, txnData] = await Promise.all([
      apiClient.get<AnalyseResponse>(`/analyse/${caseId}`),
      apiClient.get(`/transactions/${caseId}`).then((r) => r.data).catch(() => ({ transactions: [] })),
    ]);

    const transactions: any[] = Array.isArray(txnData)
      ? txnData
      : txnData.transactions ?? [];

    const chartData = buildChartData(transactions);
    console.log("CHART DATA:", chartData);
    markBackendOnline();
    setMockMode(false);

    // Inject chart data into analytics before normalising
    if (data.findings?.analytics) {
      Object.assign(data.findings.analytics, chartData);
    } else if (data.findings) {
      data.findings.analytics = { ...chartData };
    }

    return normaliseAnalysis(data, _uploadCache[caseId]);
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      return normaliseAnalysis(await mockFetchAnalysis(caseId), _uploadCache[caseId]);
    }
    throw err;
  }
}

export async function fetchTransactions(caseId: string): Promise<Transaction[]> {
  if (shouldSkipBackend()) {
    setMockMode(true);
    return mockFetchTransactions(caseId);
  }

  try {
    const { data } = await apiClient.get<Transaction[] | { transactions: Transaction[] }>(
      `/transactions/${caseId}`
    );
    markBackendOnline();
    setMockMode(false);
    return Array.isArray(data) ? data : data.transactions ?? [];
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      return mockFetchTransactions(caseId);
    }
    throw err;
  }
}

export async function fetchCases(): Promise<CaseSummary[]> {
  if (shouldSkipBackend()) {
    setMockMode(true);
    return mockFetchCases();
  }

  try {
    const { data } = await apiClient.get<CaseSummary[] | { cases: CaseSummary[] }>("/cases");
    markBackendOnline();
    setMockMode(false);
    return Array.isArray(data) ? data : data.cases ?? [];
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      return mockFetchCases();
    }
    throw err;
  }
}

export async function cleanStatement(file: File): Promise<CleanResponse> {
  if (shouldSkipBackend()) {
    setMockMode(true);
    return mockCleanStatement(file);
  }

  try {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await apiClient.post<CleanResponse>("/api/clean", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    markBackendOnline();
    setMockMode(false);
    return data;
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      return mockCleanStatement(file);
    }
    throw err;
  }
}