import type {
  Analytics,
  Transaction,
  FindingsGraph,
  GraphNode,
  GraphEdge,
  RoundTrip,
  AIBrief,
  IdentityInfo,
  AlertItem,
  Findings,
} from "../types";

// ---- Deterministic seeded RNG (mulberry32) so the same case_id always
// produces the same mock data, without having to persist large payloads. ----
function hashString(str: string): number {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return h >>> 0;
}

function mulberry32(seed: number) {
  let a = seed;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function seededRandom(seedStr: string) {
  return mulberry32(hashString(seedStr));
}

function pick<T>(rng: () => number, arr: T[]): T {
  return arr[Math.floor(rng() * arr.length)];
}

function randInt(rng: () => number, min: number, max: number): number {
  return Math.floor(rng() * (max - min + 1)) + min;
}

const FIRST_NAMES = ["Ramesh", "Suresh", "Anita", "Priya", "Vikram", "Deepa", "Arjun", "Kavya", "Manoj", "Sneha"];
const LAST_NAMES = ["Kumar", "Rao", "Nair", "Gowda", "Reddy", "Shetty", "Iyer", "Naik", "Bhat", "Prasad"];
const BANKS = ["State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank", "Canara Bank", "Union Bank of India"];
const BRANCHES = ["MG Road, Bengaluru", "Koramangala, Bengaluru", "Indiranagar, Bengaluru", "Jayanagar, Bengaluru", "Whitefield, Bengaluru"];
const MERCHANTS = ["Amazon Pay", "Flipkart", "Swiggy", "Zomato", "PhonePe", "Google Pay UPI", "IRCTC", "BESCOM", "Reliance Retail", "BigBasket"];
const DESCRIPTIONS_DEBIT = ["UPI/", "NEFT DR/", "IMPS DR/", "ATM WDL/", "CHQ WDL/", "POS PURCHASE/"];
const DESCRIPTIONS_CREDIT = ["UPI/", "NEFT CR/", "IMPS CR/", "SALARY CR/", "CASH DEP/", "RTGS CR/"];

function randomName(rng: () => number) {
  return `${pick(rng, FIRST_NAMES)} ${pick(rng, LAST_NAMES)}`;
}

function randomAccountNumber(rng: () => number) {
  return String(randInt(rng, 10000000, 99999999)) + String(randInt(rng, 1000, 9999));
}

function randomIFSC(rng: () => number) {
  const bankCode = pick(rng, ["SBIN", "HDFC", "ICIC", "UTIB", "CNRB", "UBIN"]);
  return `${bankCode}0${String(randInt(rng, 100000, 999999)).slice(0, 6)}`;
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

export function generateIdentity(seedStr: string, caseId: string): IdentityInfo {
  const rng = seededRandom(seedStr + ":identity");
  return {
    account_holder: randomName(rng),
    account_number: randomAccountNumber(rng),
    bank: pick(rng, BANKS),
    branch: pick(rng, BRANCHES),
    ifsc: randomIFSC(rng),
    email: "redacted@example.com",
    investigation_id: caseId,
    upload_time: daysAgo(randInt(rng, 0, 5)),
    sha256: Array.from({ length: 64 }, () => "0123456789abcdef"[randInt(rng, 0, 15)]).join(""),
    md5: Array.from({ length: 32 }, () => "0123456789abcdef"[randInt(rng, 0, 15)]).join(""),
  };
}

export function generateTransactions(seedStr: string, count = 60): Transaction[] {
  const rng = seededRandom(seedStr + ":transactions");
  const txns: Transaction[] = [];
  let balance = randInt(rng, 50000, 400000);

  for (let i = count; i >= 0; i--) {
    const isCredit = rng() > 0.52;
    const isCash = rng() > 0.82;
    const isFailed = rng() > 0.94;
    const isReversal = !isFailed && rng() > 0.95;
    const amount = isCash
      ? randInt(rng, 500, 40000)
      : Math.round((randInt(rng, 100, 250000) + rng()) * 100) / 100;

    const desc = isCredit ? pick(rng, DESCRIPTIONS_CREDIT) : pick(rng, DESCRIPTIONS_DEBIT);
    const merchant = pick(rng, MERCHANTS);
    const refNo = randInt(rng, 100000000000, 999999999999);

    if (isCredit) balance += amount;
    else balance -= amount;

    txns.push({
      date: daysAgo(i),
      description: `${desc}${merchant}/${refNo}`,
      debit: !isCredit ? amount : undefined,
      credit: isCredit ? amount : undefined,
      balance: Math.round(balance * 100) / 100,
      status: isFailed ? "Failed" : isReversal ? "Reversed" : "Success",
      transaction_type: isCash ? "Cash" : rng() > 0.5 ? "UPI" : "Digital",
      source: !isCredit ? "Self A/C" : `${merchant} A/C ${randInt(rng, 1000, 9999)}`,
      destination: isCredit ? "Self A/C" : `${merchant} A/C ${randInt(rng, 1000, 9999)}`,
    });
  }

  return txns.reverse();
}

export function deriveAnalytics(seedStr: string, txns: Transaction[]): Analytics {
  const rng = seededRandom(seedStr + ":analytics");
  const totalDebit = txns.reduce((s, t) => s + (t.debit || 0), 0);
  const totalCredit = txns.reduce((s, t) => s + (t.credit || 0), 0);
  const failed = txns.filter((t) => t.status === "Failed").length;
  const reversed = txns.filter((t) => t.status === "Reversed").length;
  const cash = txns.filter((t) => t.transaction_type === "Cash").length;

  const byDate = new Map<string, { count: number; debit: number; credit: number }>();
  for (const t of txns) {
    const day = t.date.slice(0, 10);
    const entry = byDate.get(day) || { count: 0, debit: 0, credit: 0 };
    entry.count += 1;
    entry.debit += t.debit || 0;
    entry.credit += t.credit || 0;
    byDate.set(day, entry);
  }
  const dailyEntries = Array.from(byDate.entries()).slice(-14);

  let cumulative = 0;
  const timeline = dailyEntries.map(([date, v]) => {
    cumulative += v.credit - v.debit;
    return { date, value: Math.round(cumulative) };
  });

  return {
    total_transactions: txns.length,
    total_debit: Math.round(totalDebit),
    total_credit: Math.round(totalCredit),
    net_flow: Math.round(totalCredit - totalDebit),
    failed_transactions: failed,
    reversal_transactions: reversed,
    cash_withdrawals: cash,
    cheque_withdrawals: randInt(rng, 0, 6),
    unsourced_debits: randInt(rng, 0, 5),
    fifo_status: "Consistent",
    balance_audit_status: "Matched",
    daily_transactions: dailyEntries.map(([date, v]) => ({ date, count: v.count, amount: Math.round(v.debit + v.credit) })),
    debit_vs_credit: dailyEntries.map(([date, v]) => ({ date, debit: Math.round(v.debit), credit: Math.round(v.credit) })),
    transaction_types: [
      { type: "UPI", value: txns.filter((t) => t.transaction_type === "UPI").length },
      { type: "Digital", value: txns.filter((t) => t.transaction_type === "Digital").length },
      { type: "Cash", value: cash },
    ],
    cash_vs_digital: [
      { name: "Cash", value: cash },
      { name: "Digital", value: txns.length - cash },
    ],
    timeline,
  };
}

export function generateGraph(seedStr: string): FindingsGraph {
  const rng = seededRandom(seedStr + ":graph");
  const nodeCount = randInt(rng, 6, 9);
  const risks = ["low", "medium", "high"];
  const nodes: GraphNode[] = Array.from({ length: nodeCount }, (_, i) => ({
    id: `acc_${i}`,
    label: i === 0 ? "Primary Account" : `${pick(rng, MERCHANTS)} A/C ${randInt(rng, 100, 999)}`,
    account: randomAccountNumber(rng),
    risk: i === 0 ? "low" : pick(rng, risks),
    total_inflow: randInt(rng, 10000, 500000),
    total_outflow: randInt(rng, 10000, 500000),
  }));

  const edges: GraphEdge[] = [];
  for (let i = 1; i < nodeCount; i++) {
    edges.push({
      id: `e_${i}`,
      source: "acc_0",
      target: `acc_${i}`,
      amount: randInt(rng, 5000, 200000),
      risk: nodes[i].risk,
    });
    if (rng() > 0.6 && i < nodeCount - 1) {
      edges.push({
        id: `e_loop_${i}`,
        source: `acc_${i}`,
        target: `acc_${i + 1}`,
        amount: randInt(rng, 5000, 100000),
        risk: pick(rng, risks),
      });
    }
  }

  return { nodes, edges };
}

export function generateRoundTrips(seedStr: string, graph: FindingsGraph): RoundTrip[] {
  const rng = seededRandom(seedStr + ":roundtrips");
  const count = randInt(rng, 0, 3);
  const accountIds = graph.nodes.map((n) => n.id);
  const loops: RoundTrip[] = [];

  for (let i = 0; i < count; i++) {
    const hops = randInt(rng, 3, 5);
    const accounts = Array.from({ length: hops }, () => pick(rng, accountIds));
    loops.push({
      loop_id: `LOOP-${String(i + 1).padStart(3, "0")}`,
      accounts,
      hop_count: hops,
      amount: randInt(rng, 20000, 400000),
      risk: pick(rng, ["medium", "high", "critical"]),
      timeline: Array.from({ length: hops }, (_, h) => daysAgo(hops - h)),
    });
  }
  return loops;
}

export function generateAIBrief(seedStr: string, analytics: Analytics, loops: RoundTrip[]): AIBrief {
  const rng = seededRandom(seedStr + ":aibrief");
  const riskLevel = loops.length > 1 ? "elevated" : loops.length === 1 ? "moderate" : "low";
  return {
    risk_summary: `Based on ${analytics.total_transactions ?? 0} analysed transactions, this account shows a ${riskLevel} money-laundering risk profile. ${
      loops.length > 0
        ? `${loops.length} circular fund-transfer loop(s) were detected involving linked accounts.`
        : "No circular fund-transfer patterns were detected."
    }`,
    key_findings: [
      `${analytics.failed_transactions ?? 0} failed transaction(s) and ${analytics.reversal_transactions ?? 0} reversal(s) identified.`,
      `${analytics.cash_withdrawals ?? 0} cash withdrawal event(s) flagged for manual review.`,
      loops.length > 0
        ? `Largest detected loop cycles ₹${(loops[0].amount || 0).toLocaleString("en-IN")} across ${loops[0].hop_count} accounts.`
        : "Balance ledger is internally consistent across the statement period.",
    ],
    important_entities: Array.from({ length: randInt(rng, 2, 4) }, () => randomName(rng)),
    recommendations: [
      "Cross-verify high-value UPI counterparties against known mule account databases.",
      "Request 90-day statements for linked secondary accounts identified in the money-flow graph.",
      loops.length > 0 ? "Escalate round-tripping loops for Section 65B evidence certification." : "Continue routine monitoring; no immediate escalation required.",
    ],
  };
}

export function generateAlerts(seedStr: string, loops: RoundTrip[]): AlertItem[] {
  const rng = seededRandom(seedStr + ":alerts");
  const alerts: AlertItem[] = [];
  if (loops.length > 0) {
    alerts.push({
      id: "alert-1",
      title: `${loops.length} round-tripping loop(s) detected`,
      severity: "high",
      description: "Circular fund movement suggests possible layering activity.",
      timestamp: daysAgo(0),
    });
  }
  if (rng() > 0.4) {
    alerts.push({
      id: "alert-2",
      title: "Unusual cash withdrawal velocity",
      severity: "medium",
      description: "Multiple cash withdrawals within a short window were detected.",
      timestamp: daysAgo(1),
    });
  }
  if (rng() > 0.6) {
    alerts.push({
      id: "alert-3",
      title: "Large unsourced credit",
      severity: "medium",
      description: "A high-value credit entry could not be traced to a verified source account.",
      timestamp: daysAgo(2),
    });
  }
  return alerts;
}

export function generateFindings(seedStr: string, caseId: string): Findings {
  const txns = generateTransactions(seedStr);
  const analytics = deriveAnalytics(seedStr, txns);
  const graph = generateGraph(seedStr);
  const roundTrips = generateRoundTrips(seedStr, graph);
  const identity = generateIdentity(seedStr, caseId);
  const aiBrief = generateAIBrief(seedStr, analytics, roundTrips);
  const alerts = generateAlerts(seedStr, roundTrips);
  const failedTxns = txns.filter((t) => t.status === "Failed");
  const reversalTxns = txns.filter((t) => t.status === "Reversed");

  const rng = seededRandom(seedStr + ":lists");
  return {
    analytics,
    graph,
    round_trips: roundTrips,
    ai_brief: aiBrief,
    identity,
    failed_transactions: failedTxns,
    reversal_transactions: reversalTxns,
    velocity_anomalies: Array.from({ length: randInt(rng, 0, 3) }, () => `${randInt(rng, 3, 9)} txns within 10 minutes on ${daysAgo(randInt(rng, 1, 10)).slice(0, 10)}`),
    most_active_upi: Array.from({ length: 3 }, () => `${pick(rng, MERCHANTS).toLowerCase().replace(/\s+/g, "")}@upi`),
    most_active_accounts: graph.nodes.slice(0, 3).map((n) => n.label),
    highest_risk_accounts: graph.nodes.filter((n) => n.risk === "high").map((n) => n.label),
    alerts,
  };
}

export function generateCaseSummary(caseId: string): {
  case_id: string;
  account_holder: string;
  bank: string;
  upload_date: string;
  transactions: number;
  status: string;
} {
  const rng = seededRandom(caseId + ":summary");
  return {
    case_id: caseId,
    account_holder: randomName(rng),
    bank: pick(rng, BANKS),
    upload_date: new Date().toISOString(),
    transactions: randInt(rng, 40, 90),
    status: "Processed",
  };
}
