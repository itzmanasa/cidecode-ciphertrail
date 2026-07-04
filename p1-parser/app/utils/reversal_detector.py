"""
reversal_detector.py — CRITICAL Day 2 Evening Component
=====================================================
Detects THREE types of anomalies — this is the MAIN JUDGING PARAMETER.

TYPE 1 — EXPLICIT: Transaction already marked FAILED/REVERSAL in its own statement.
  → Already caught by _detect_status() in pdf_parser.py during parsing.

TYPE 2 — CROSS-ACCOUNT (the hard one, repeated by judges):
  "Debit in Bank A but no matching credit appears in Bank B within a time window."
  → A₁ sends money, B never receives it. Real forensic finding.
  → Requires comparing statements from MULTIPLE uploaded accounts.

TYPE 3 — ROUND-TRIP REVERSAL (within same account):
  Money leaves A → comes back to A. Disguised reversal.
  Full multi-account round-tripping (A→B→C→A) is handled by P2's NetworkX graph.

Usage:
  from app.utils.reversal_detector import analyze_reversals
  result = analyze_reversals(statements_list)

statements_list = list of BankStatement dicts (one per uploaded file).
"""

from datetime import datetime, timedelta
from typing import List, Optional
import logging
import re

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
MATCH_WINDOW_DAYS   = 3      # Days to look for matching credit after a debit
AMOUNT_TOLERANCE_PCT = 0.02  # 2% tolerance (handles bank charges)
AMOUNT_TOLERANCE_ABS = 50.0  # OR within ₹50 absolute


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(str(date_str)[:10], fmt)
        except ValueError:
            continue
    return None


def _amounts_match(a: float, b: float) -> bool:
    if a == 0 or b == 0:
        return False
    diff = abs(a - b)
    return diff <= AMOUNT_TOLERANCE_ABS or (diff / max(a, b)) <= AMOUNT_TOLERANCE_PCT


def _extract_counterparty_account(particulars: str) -> Optional[str]:
    """Pull counterparty account number from narration text."""
    patterns = [
        r"(?:to|from)\s+a[/]?c\s*[:\-]?\s*(\d{8,20})",
        r"(?:to|from)\s+acc(?:ount)?\s*[:\-]?\s*(\d{8,20})",
        r"\b(\d{10,16})\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, particulars.lower())
        if m:
            return m.group(1)
    return None


# ── Type 1: Explicit failures (already parsed) ────────────────────────────────

def flag_explicit_failures(statements: List[dict]) -> List[dict]:
    """Surface all FAILED/REVERSAL transactions across all statements."""
    results = []
    for stmt in statements:
        acc  = stmt.get("account_number", "UNKNOWN")
        bank = stmt.get("bank_name", "UNKNOWN")
        for txn in stmt.get("transactions", []):
            if txn.get("status") in ("FAILED", "REVERSAL"):
                results.append({
                    "anomaly_type": "EXPLICIT_FAILURE",
                    "severity":     "HIGH" if txn.get("status") == "FAILED" else "MEDIUM",
                    "account":      acc,
                    "bank":         bank,
                    "txn_id":       txn.get("txn_id"),
                    "date":         txn.get("date"),
                    "amount":       txn.get("debit", 0) or txn.get("credit", 0),
                    "particulars":  txn.get("particulars"),
                    "status":       txn.get("status"),
                    "description":  (
                        f"{txn.get('status')} transaction of ₹{txn.get('debit',0) or txn.get('credit',0):,.2f} "
                        f"on {txn.get('date')} in account {acc}. "
                        f"Must be EXCLUDED from balance audit to avoid absurd results."
                    ),
                    "flag": f"{txn.get('status')}_TXN",
                })
    return results


# ── Type 2: Cross-account unmatched debits ────────────────────────────────────

def find_unmatched_debits(statements: List[dict]) -> List[dict]:
    """
    For every successful DEBIT in any account:
    Search all other accounts for a matching CREDIT within MATCH_WINDOW_DAYS.
    If none found → UNMATCHED_DEBIT anomaly.
    This is the Layer 1 / Layer 2 check the judges keep mentioning.
    """
    anomalies = []

    # Index all successful credits across all accounts
    all_credits = []
    for stmt in statements:
        acc = stmt.get("account_number", "UNKNOWN")
        for txn in stmt.get("transactions", []):
            if txn.get("txn_type") == "CREDIT" and txn.get("status") == "SUCCESS":
                d = _to_date(txn.get("date", ""))
                if d:
                    all_credits.append({
                        "account": acc,
                        "amount":  txn.get("credit", 0.0),
                        "date":    d,
                        "txn_id":  txn.get("txn_id"),
                    })

    # Check each successful debit
    for stmt in statements:
        acc_a  = stmt.get("account_number", "UNKNOWN")
        bank_a = stmt.get("bank_name", "UNKNOWN")

        for txn in stmt.get("transactions", []):
            if txn.get("txn_type") != "DEBIT":
                continue
            if txn.get("status") != "SUCCESS":
                continue

            amount = txn.get("debit", 0.0)
            if amount <= 0:
                continue

            debit_date = _to_date(txn.get("date", ""))
            if not debit_date:
                continue

            # Search for matching credit in any OTHER account
            matched = any(
                c["account"] != acc_a
                and _amounts_match(amount, c["amount"])
                and abs((c["date"] - debit_date).days) <= MATCH_WINDOW_DAYS
                for c in all_credits
            )

            if not matched:
                counterparty = _extract_counterparty_account(txn.get("particulars", ""))
                anomalies.append({
                    "anomaly_type":               "UNMATCHED_DEBIT",
                    "severity":                   "HIGH",
                    "source_account":             acc_a,
                    "source_bank":                bank_a,
                    "txn_id":                     txn.get("txn_id"),
                    "date":                       txn.get("date"),
                    "amount":                     amount,
                    "particulars":                txn.get("particulars"),
                    "intended_recipient_account": counterparty,
                    "description": (
                        f"₹{amount:,.2f} debited from {acc_a} ({bank_a}) on {txn.get('date')} "
                        f"— no matching credit found in any linked account within {MATCH_WINDOW_DAYS} days. "
                        f"Money may have been reversed, failed silently, or gone to an unlinked account."
                    ),
                    "flag": "LAYER_1_REVERSAL_CANDIDATE",
                })

    return anomalies


# ── Type 3: Round-trip reversals (within same account) ───────────────────────

def find_roundtrip_reversals(statements: List[dict]) -> List[dict]:
    """
    Within each account: find DEBIT followed by same-amount CREDIT within 30 days.
    Indicates money left and came back — classic reversal disguise.
    """
    anomalies = []

    for stmt in statements:
        acc  = stmt.get("account_number", "UNKNOWN")
        bank = stmt.get("bank_name", "UNKNOWN")
        txns = stmt.get("transactions", [])

        debits  = [t for t in txns if t.get("txn_type") == "DEBIT"   and t.get("status") == "SUCCESS" and t.get("debit",  0) > 0]
        credits = [t for t in txns if t.get("txn_type") == "CREDIT"  and t.get("status") == "SUCCESS" and t.get("credit", 0) > 0]

        for d_txn in debits:
            d_date   = _to_date(d_txn.get("date", ""))
            d_amount = d_txn.get("debit", 0.0)
            if not d_date:
                continue

            for c_txn in credits:
                c_date   = _to_date(c_txn.get("date", ""))
                c_amount = c_txn.get("credit", 0.0)
                if not c_date or c_date <= d_date:
                    continue

                days_apart = (c_date - d_date).days
                if days_apart <= 30 and _amounts_match(d_amount, c_amount):
                    anomalies.append({
                        "anomaly_type":  "ROUNDTRIP_REVERSAL",
                        "severity":      "MEDIUM",
                        "account":       acc,
                        "bank":          bank,
                        "debit_txn_id":  d_txn.get("txn_id"),
                        "credit_txn_id": c_txn.get("txn_id"),
                        "debit_date":    d_txn.get("date"),
                        "credit_date":   c_txn.get("date"),
                        "amount":        d_amount,
                        "days_apart":    days_apart,
                        "description": (
                            f"₹{d_amount:,.2f} left account {acc} on {d_txn.get('date')} "
                            f"and returned {days_apart} days later on {c_txn.get('date')}. "
                            f"Possible round-trip or reversal disguised as two real transactions."
                        ),
                        "flag": "ROUNDTRIP_REVERSAL",
                    })

    return anomalies


# ── Main entry ────────────────────────────────────────────────────────────────

def analyze_reversals(statements: List[dict]) -> dict:
    """
    Run all reversal checks on a list of BankStatement dicts.
    Returns structured anomaly report for P2 to store and P3 to display.
    """
    explicit   = flag_explicit_failures(statements)
    unmatched  = find_unmatched_debits(statements)
    roundtrips = find_roundtrip_reversals(statements)

    total = len(explicit) + len(unmatched) + len(roundtrips)

    logger.info(
        f"Reversal analysis: {len(explicit)} explicit, "
        f"{len(unmatched)} unmatched debits, {len(roundtrips)} roundtrips"
    )

    return {
        "total_anomalies":        total,
        "explicit_failures":      explicit,
        "unmatched_debits":       unmatched,
        "roundtrip_reversals":    roundtrips,
        "match_window_days_used": MATCH_WINDOW_DAYS,
        "summary": {
            "explicit_failure_count":   len(explicit),
            "unmatched_debit_count":    len(unmatched),
            "roundtrip_reversal_count": len(roundtrips),
        },
    }
