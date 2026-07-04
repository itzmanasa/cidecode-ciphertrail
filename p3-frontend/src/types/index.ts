// ---- Upload / Case ----
export interface UploadResponse {
  case_id: string;
  file_name?: string;
  file_hash?: string;
  total_transactions?: number;
  reversals_found?: number;
  account_id?: string;
  owner_name?: string;
  bank_name?: string;
  period_from?: string;
  period_to?: string;
  audit?: {
    duplicates_removed?: number;
    balance_audit_clean?: boolean;
    total_debit?: number;
    total_credit?: number;
    cash_withdrawal_count?: number;
    cash_withdrawal_total?: number;
    cheque_withdrawal_count?: number;
    cheque_withdrawal_total?: number;
  };
  [key: string]: unknown;
}

export interface CaseSummary {
  case_id: string;
  account_holder?: string;
  bank?: string;
  upload_date?: string;
  transactions?: number;
  status?: string;
  [key: string]: unknown;
}

// ---- Graph (React Flow) ----
export interface GraphNode {
  id: string;
  label?: string;
  account?: string;
  risk?: "low" | "medium" | "high" | string;
  total_inflow?: number;
  total_outflow?: number;
  [key: string]: unknown;
}

export interface GraphEdge {
  id?: string;
  source: string;
  target: string;
  amount?: number;
  label?: string;
  risk?: string;
  [key: string]: unknown;
}

export interface FindingsGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ---- Round Trips ----
export interface RoundTrip {
  loop_id: string;
  accounts: string[];
  hop_count: number;
  amount: number;
  transactions?: Transaction[];
  timeline?: string[];
  risk?: "low" | "medium" | "high" | string;
  [key: string]: unknown;
}

// ---- Analytics ----
export interface Analytics {
  total_transactions?: number;
  total_debit?: number;
  total_credit?: number;
  net_flow?: number;
  failed_transactions?: number;
  reversal_transactions?: number;
  cash_withdrawals?: number;
  cheque_withdrawals?: number;
  unsourced_debits?: number;
  fifo_status?: string;
  balance_audit_status?: string;
  daily_transactions?: { date: string; count: number; amount?: number }[];
  debit_vs_credit?: { date: string; debit: number; credit: number }[];
  transaction_types?: { type: string; value: number }[];
  cash_vs_digital?: { name: string; value: number }[];
  timeline?: { date: string; value: number }[];
  [key: string]: unknown;
}

// ---- Findings ----
export interface Findings {
  analytics: Analytics;
  graph: FindingsGraph;
  round_trips: RoundTrip[];
  ai_brief: string | AIBrief;
  identity?: IdentityInfo;
  failed_transactions?: Transaction[];
  reversal_transactions?: Transaction[];
  velocity_anomalies?: unknown[];
  top_accounts?: unknown[];
  most_active_upi?: unknown[];
  most_active_accounts?: unknown[];
  highest_risk_accounts?: unknown[];
  alerts?: AlertItem[];
  [key: string]: unknown;
}

export interface AIBrief {
  key_findings?: string[];
  risk_summary?: string;
  important_entities?: string[];
  recommendations?: string[];
  [key: string]: unknown;
}

export interface AlertItem {
  id: string;
  title: string;
  severity: "low" | "medium" | "high" | "critical" | string;
  description?: string;
  timestamp?: string;
}

export interface IdentityInfo {
  account_holder?: string;
  account_number?: string;
  bank?: string;
  branch?: string;
  ifsc?: string;
  email?: string;
  investigation_id?: string;
  upload_time?: string;
  sha256?: string;
  md5?: string;
  [key: string]: unknown;
}

export interface AnalyseResponse {
  case_id: string;
  findings: Findings;
  [key: string]: unknown;
}

// ---- Transactions ----
export interface Transaction {
  date: string;
  description: string;
  debit?: number;
  credit?: number;
  balance?: number;
  status?: string;
  transaction_type?: string;
  source?: string;
  destination?: string;
  [key: string]: unknown;
}

// ---- /api/clean ----
export interface BankStatement {
  account_holder?: string;
  account_number?: string;
  bank?: string;
  transactions?: Transaction[];
  [key: string]: unknown;
}

export interface CleanResponse {
  success: boolean;
  statement: BankStatement;
  audit_results: Record<string, unknown>;
  summary_stats: Record<string, unknown>;
}
