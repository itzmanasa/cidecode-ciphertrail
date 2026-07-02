import jsPDF from "jspdf";
import type { AnalyseResponse, RoundTrip } from "../types";
import { formatINR, formatDate } from "../utils/format";

const PRIMARY: [number, number, number] = [79, 70, 229];
const INK: [number, number, number] = [15, 23, 42];
const MUTED: [number, number, number] = [100, 116, 139];
const PAGE_W = 210;
const PAGE_H = 297;
const MARGIN = 16;

function header(doc: jsPDF, title: string, pageNum: number) {
  doc.setFillColor(...PRIMARY);
  doc.rect(0, 0, PAGE_W, 22, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(13);
  doc.setFont("helvetica", "bold");
  doc.text("CipherTrail — Karnataka CID Cyber Crime Unit", MARGIN, 14);
  doc.setFontSize(9);
  doc.setFont("helvetica", "normal");
  doc.text(title, MARGIN, 19);
  doc.setTextColor(...MUTED);
  doc.setFontSize(8);
  doc.text(`Page ${pageNum}`, PAGE_W - MARGIN - 10, 19);
}

function footer(doc: jsPDF) {
  doc.setDrawColor(226, 232, 240);
  doc.line(MARGIN, PAGE_H - 14, PAGE_W - MARGIN, PAGE_H - 14);
  doc.setFontSize(7.5);
  doc.setTextColor(...MUTED);
  doc.text("CONFIDENTIAL — For official investigative use only under the IT Act, 2000 and BSA, 2023.", MARGIN, PAGE_H - 9);
}

function sectionTitle(doc: jsPDF, text: string, y: number) {
  doc.setTextColor(...INK);
  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  doc.text(text, MARGIN, y);
  doc.setDrawColor(...PRIMARY);
  doc.setLineWidth(0.6);
  doc.line(MARGIN, y + 1.5, MARGIN + 18, y + 1.5);
  return y + 9;
}

function kv(doc: jsPDF, label: string, value: string, x: number, y: number, w: number) {
  doc.setFontSize(7.5);
  doc.setTextColor(...MUTED);
  doc.text(label.toUpperCase(), x, y);
  doc.setFontSize(9.5);
  doc.setTextColor(...INK);
  doc.setFont("helvetica", "bold");
  doc.text(doc.splitTextToSize(value || "—", w), x, y + 5);
  doc.setFont("helvetica", "normal");
}

export function generateEvidenceReport(analysis: AnalyseResponse) {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const f = analysis.findings;
  const a = f.analytics;
  const identity = f.identity;
  let page = 1;

  // Page 1: Identity + Analytics
  header(doc, "Evidence Report", page);
  let y = 34;
  y = sectionTitle(doc, "Case Identity", y);
  doc.setFillColor(245, 247, 251);
  doc.roundedRect(MARGIN, y - 5, PAGE_W - MARGIN * 2, 38, 2, 2, "F");
  const fields: [string, string][] = [
    ["Account Holder", identity?.account_holder || "—"],
    ["Bank", identity?.bank || "—"],
    ["Account Number", identity?.account_number || "—"],
    ["IFSC", identity?.ifsc || "—"],
    ["Investigation ID", identity?.investigation_id || analysis.case_id],
    ["Upload Time", formatDate(identity?.upload_time)],
  ];
  fields.forEach((field, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    kv(doc, field[0], field[1], MARGIN + 4 + col * 60, y + 4 + row * 16, 56);
  });
  y += 42;

  y = sectionTitle(doc, "Analytics Summary", y);
  const stats: [string, string][] = [
    ["Total Transactions", String(a?.total_transactions ?? "—")],
    ["Total Debit", formatINR(a?.total_debit)],
    ["Total Credit", formatINR(a?.total_credit)],
    ["Net Flow", formatINR(a?.net_flow)],
    ["Failed Transactions", String(a?.failed_transactions ?? "—")],
    ["Reversal Transactions", String(a?.reversal_transactions ?? "—")],
    ["Cash Withdrawals", String(a?.cash_withdrawals ?? "—")],
    ["FIFO Status", String(a?.fifo_status ?? "—")],
    ["Balance Audit Status", String(a?.balance_audit_status ?? "—")],
  ];
  stats.forEach((s, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = MARGIN + col * 60;
    const sy = y + row * 18;
    doc.setFillColor(255, 255, 255);
    doc.setDrawColor(226, 232, 240);
    doc.roundedRect(x, sy - 5, 56, 15, 2, 2, "FD");
    kv(doc, s[0], s[1], x + 3, sy + 1, 50);
  });
  y += Math.ceil(stats.length / 3) * 18 + 6;

  y = sectionTitle(doc, "AI Investigation Summary", y);
  doc.setFontSize(9);
  doc.setTextColor(...INK);
  const briefText = typeof f.ai_brief === "string" ? f.ai_brief : f.ai_brief?.risk_summary || "No AI brief available.";
  const lines = doc.splitTextToSize(briefText, PAGE_W - MARGIN * 2);
  doc.text(lines.slice(0, 8), MARGIN, y);
  footer(doc);

  // Page 2: Round Trips
  doc.addPage();
  page++;
  header(doc, "Round Tripping Analysis", page);
  y = 34;
  y = sectionTitle(doc, `Round Trips Detected (${f.round_trips?.length ?? 0})`, y);
  (f.round_trips ?? []).slice(0, 8).forEach((loop: RoundTrip) => {
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(MARGIN, y - 5, PAGE_W - MARGIN * 2, 18, 2, 2, "F");
    doc.setFontSize(9.5);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(...INK);
    doc.text(`Loop ${loop.loop_id} — ${loop.risk?.toString().toUpperCase() || "LOW"} RISK`, MARGIN + 3, y + 1);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(...MUTED);
    doc.text(`${loop.accounts.join(" -> ")} -> ${loop.accounts[0]}`, MARGIN + 3, y + 6);
    doc.text(`Amount: ${formatINR(loop.amount)}   Hops: ${loop.hop_count}`, MARGIN + 3, y + 11);
    y += 22;
  });
  if (!f.round_trips || f.round_trips.length === 0) {
    doc.setFontSize(9);
    doc.setTextColor(...MUTED);
    doc.text("No circular fund-transfer loops were detected for this case.", MARGIN, y);
  }
  footer(doc);

  // Page 3: Audit + Certificate
  doc.addPage();
  page++;
  header(doc, "Audit Results & Certification", page);
  y = 34;
  y = sectionTitle(doc, "Audit Results", y);
  doc.setFontSize(9);
  doc.setTextColor(...INK);
  doc.text(`FIFO Status: ${a?.fifo_status ?? "—"}`, MARGIN, y);
  doc.text(`Balance Audit Status: ${a?.balance_audit_status ?? "—"}`, MARGIN, y + 6);
  doc.text(`Unsourced Debits: ${a?.unsourced_debits ?? "—"}`, MARGIN, y + 12);
  y += 24;

  y = sectionTitle(doc, "Section 65B Certificate", y);
  doc.setFillColor(245, 247, 251);
  doc.roundedRect(MARGIN, y - 5, PAGE_W - MARGIN * 2, 60, 2, 2, "F");
  doc.setFontSize(8.5);
  doc.setTextColor(...INK);
  const cert = doc.splitTextToSize(
    "I certify, under Section 65B of the Indian Evidence Act, 1872 (as carried forward under the Bharatiya Sakshya Adhiniyam, 2023), " +
      "that the electronic record reproduced in this report was produced by a computer used regularly for processing information for the " +
      "purposes of this investigation, and that the record accurately reproduces the original electronic data extracted from the subject " +
      "account statement, with no material alteration to its content.",
    PAGE_W - MARGIN * 2 - 8
  );
  doc.text(cert, MARGIN + 4, y + 4);

  kv(doc, "SHA256", identity?.sha256 || "—", MARGIN + 4, y + 32, 90);
  kv(doc, "MD5", identity?.md5 || "—", MARGIN + 4, y + 42, 90);
  kv(doc, "UTC Timestamp", new Date().toISOString(), MARGIN + 100, y + 32, 80);
  kv(doc, "Investigation ID", identity?.investigation_id || analysis.case_id, MARGIN + 100, y + 42, 80);

  y += 66;
  doc.setDrawColor(...MUTED);
  doc.line(MARGIN, y + 14, MARGIN + 60, y + 14);
  doc.setFontSize(8);
  doc.setTextColor(...MUTED);
  doc.text("Officer Signature", MARGIN, y + 19);
  footer(doc);

  doc.save(`CipherTrail_Evidence_Report_${analysis.case_id}.pdf`);
}
