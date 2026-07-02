"""
cleaner.py — Balance Validator + Duplicate Remover (Day 3)
==========================================================
Two responsibilities:

1. BALANCE VALIDATOR
   Checks running balance consistency across every transaction.
   Two audit modes (as per hackathon brief):

   MODE A — PRE-CREDIT BALANCE AUDIT:
     At each step: expected_balance = prev_balance + credit - debit
     If actual_balance differs by > tolerance → flag as BALANCE_MISMATCH
     CRITICAL: FAILED/REVERSAL transactions must be EXCLUDED before this check
     (if you include them, you get absurd results — judges specifically said this)

   MODE B — FIFO AUDIT:
     Match each debit to the earliest available unmatched credit.
     Flag debits that have no credit source → UNSOURCED_DEBIT
     Used to trace if "10cr from victim to accused" has a legitimate credit source.

2. DUPLICATE REMOVER
   Removes exact duplicate rows that sometimes appear when:
   - Same PDF uploaded twice
   - Bank statements overlap in date ranges
   - CBS exports repeat header rows
   Duplicate = same (date + particulars + debit + credit + balance)

3. HEADER FIELD EXTRACTOR
   Ensures account_number, branch, owner_name, bank_email are populated.
   Falls back to filename-based heuristics if metadata parsing missed them.
"""

import re
import logging
from typing import List, Dict, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Tolerance for balance mismatch (handles rounding differences)
BALANCE_TOLERANCE = 1.0   # ₹1 tolerance
FIFO_WINDOW_DAYS  = 90    # Max days to look back for credit source


# ─────────────────────────────────────────────────────────────────────────────
# DUPLICATE REMOVER
# ─────────────────────────────────────────────────────────────────────────────

def remove_duplicates(transactions: List[dict]) -> Tuple[List[dict], int]:
    """
    Remove exact duplicate transactions.
    Duplicate key = (date, particulars, debit, credit, balance).
    Keeps the first occurrence. Returns (cleaned_list, removed_count).
    """
    seen = set()
    cleaned = []
    removed = 0

    for txn in transactions:
        key = (
            str(txn.get("date", "")),
            str(txn.get("particulars", "")).strip().lower()[:80],  # first 80 chars
            round(float(txn.get("debit",   0) or 0), 2),
            round(float(txn.get("credit",  0) or 0), 2),
            round(float(txn.get("balance", 0) or 0), 2),
        )
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        cleaned.append(txn)

    if removed:
        logger.info(f"Duplicate remover: removed {removed} duplicate transactions")

    return cleaned, removed


# ─────────────────────────────────────────────────────────────────────────────
# BALANCE VALIDATOR — MODE A: PRE-CREDIT BALANCE AUDIT
# ─────────────────────────────────────────────────────────────────────────────

def pre_credit_balance_audit(transactions: List[dict]) -> dict:
    """
    Validate running balance consistency.

    IMPORTANT: Call this AFTER filtering out FAILED/REVERSAL transactions.
    If you don't filter first, every failed txn will show as a mismatch.

    Returns:
    {
        "mode": "pre_credit",
        "total_checked": N,
        "mismatches": [...],
        "mismatch_count": N,
        "opening_balance": X,
        "computed_closing_balance": X,
        "is_clean": bool
    }
    """
    # Filter out failed/reversal first
    valid_txns = [t for t in transactions if t.get("status") not in ("FAILED", "REVERSAL")]

    if not valid_txns:
        return {
            "mode": "pre_credit",
            "total_checked": 0,
            "mismatches": [],
            "mismatch_count": 0,
            "opening_balance": 0.0,
            "computed_closing_balance": 0.0,
            "is_clean": True,
        }

    # Sort by date then by raw_row_index to preserve bank's original order
    def sort_key(t):
        try:
            return (datetime.strptime(str(t.get("date", ""))[:10], "%Y-%m-%d"), t.get("raw_row_index", 0))
        except ValueError:
            return (datetime.max, t.get("raw_row_index", 0))

    sorted_txns = sorted(valid_txns, key=sort_key)

    mismatches = []
    prev_balance = sorted_txns[0].get("balance", 0.0)
    opening_balance = prev_balance

    # Start from second transaction
    for i, txn in enumerate(sorted_txns[1:], start=1):
        debit   = float(txn.get("debit",   0) or 0)
        credit  = float(txn.get("credit",  0) or 0)
        balance = float(txn.get("balance", 0) or 0)

        expected = round(prev_balance + credit - debit, 2)
        actual   = round(balance, 2)
        diff     = abs(expected - actual)

        if diff > BALANCE_TOLERANCE:
            mismatches.append({
                "txn_id":           txn.get("txn_id"),
                "date":             txn.get("date"),
                "particulars":      txn.get("particulars", "")[:60],
                "debit":            debit,
                "credit":           credit,
                "prev_balance":     round(prev_balance, 2),
                "expected_balance": expected,
                "actual_balance":   actual,
                "difference":       round(diff, 2),
                "anomaly_type":     "BALANCE_MISMATCH",
                "severity":         "HIGH" if diff > 1000 else "MEDIUM",
            })

        prev_balance = balance

    return {
        "mode":                     "pre_credit",
        "total_checked":            len(sorted_txns),
        "excluded_failed_reversal": len(transactions) - len(valid_txns),
        "mismatches":               mismatches,
        "mismatch_count":           len(mismatches),
        "opening_balance":          round(opening_balance, 2),
        "computed_closing_balance": round(prev_balance, 2),
        "is_clean":                 len(mismatches) == 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# BALANCE VALIDATOR — MODE B: FIFO AUDIT
# ─────────────────────────────────────────────────────────────────────────────

def fifo_audit(transactions: List[dict]) -> dict:
    """
    FIFO audit: match each debit to the earliest available unmatched credit.

    This answers: "Where did this money come from?"
    Judges asked: if 10cr goes from victim to accused, show the credit source.

    Algorithm:
    1. Sort all transactions by date.
    2. Maintain a pool of unmatched credits (FIFO queue).
    3. For each debit, consume from the oldest available credit.
    4. If no credit available → UNSOURCED_DEBIT (suspicious).

    Returns matched pairs + unsourced debits.
    """
    valid_txns = [t for t in transactions if t.get("status") not in ("FAILED", "REVERSAL")]

    def sort_key(t):
        try:
            return datetime.strptime(str(t.get("date", ""))[:10], "%Y-%m-%d")
        except ValueError:
            return datetime.max

    sorted_txns = sorted(valid_txns, key=sort_key)

    credit_pool = []   # List of {"amount_remaining": X, "txn": {...}}
    matched_pairs = []
    unsourced_debits = []

    for txn in sorted_txns:
        debit  = float(txn.get("debit",  0) or 0)
        credit = float(txn.get("credit", 0) or 0)

        if credit > 0:
            credit_pool.append({
                "amount_remaining": credit,
                "txn": txn,
            })

        if debit > 0:
            remaining_debit = debit
            sources = []

            for pool_entry in credit_pool:
                if remaining_debit <= 0:
                    break
                if pool_entry["amount_remaining"] <= 0:
                    continue

                used = min(remaining_debit, pool_entry["amount_remaining"])
                pool_entry["amount_remaining"] -= used
                remaining_debit -= used

                sources.append({
                    "credit_txn_id":   pool_entry["txn"].get("txn_id"),
                    "credit_date":     pool_entry["txn"].get("date"),
                    "credit_from":     pool_entry["txn"].get("particulars", "")[:60],
                    "amount_consumed": round(used, 2),
                })

            if remaining_debit > BALANCE_TOLERANCE:
                unsourced_debits.append({
                    "txn_id":           txn.get("txn_id"),
                    "date":             txn.get("date"),
                    "particulars":      txn.get("particulars", "")[:60],
                    "debit_amount":     debit,
                    "unsourced_amount": round(remaining_debit, 2),
                    "anomaly_type":     "UNSOURCED_DEBIT",
                    "severity":         "HIGH",
                    "description": (
                        f"₹{remaining_debit:,.2f} of debit on {txn.get('date')} "
                        f"has no matching credit source in FIFO pool."
                    ),
                })
            elif sources:
                matched_pairs.append({
                    "debit_txn_id": txn.get("txn_id"),
                    "debit_date":   txn.get("date"),
                    "debit_amount": debit,
                    "sources":      sources,
                })

    # Remaining unspent credits
    unspent_credits = [
        {
            "txn_id":            e["txn"].get("txn_id"),
            "date":              e["txn"].get("date"),
            "particulars":       e["txn"].get("particulars", "")[:60],
            "unspent_amount":    round(e["amount_remaining"], 2),
        }
        for e in credit_pool if e["amount_remaining"] > BALANCE_TOLERANCE
    ]

    return {
        "mode":              "fifo",
        "total_checked":     len(sorted_txns),
        "matched_pairs":     matched_pairs,
        "unsourced_debits":  unsourced_debits,
        "unsourced_count":   len(unsourced_debits),
        "unspent_credits":   unspent_credits,
        "is_clean":          len(unsourced_debits) == 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# HEADER FIELD EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────

def extract_header_fields(statement: dict) -> dict:
    """
    Ensure all key header fields are populated.
    Fills gaps using filename heuristics if parser missed them.
    Returns enriched statement dict (does not mutate original).
    """
    result = dict(statement)
    filename = result.get("source_file", "")

    # Account number from filename if missing
    if result.get("account_number") in (None, "UNKNOWN", ""):
        acc_match = re.search(r"(\d{9,18})", filename)
        if acc_match:
            result["account_number"] = acc_match.group(1)
            result.setdefault("parse_warnings", []).append(
                f"account_number extracted from filename: {acc_match.group(1)}"
            )

    # Owner name from filename (e.g. "KOMAL statement", "DEVANSHU_STMNT")
    if result.get("owner_name") in (None, "UNKNOWN", ""):
        name_match = re.match(r"^([A-Z][A-Z\s]+?)[\s_\-]", filename.upper())
        if name_match:
            candidate = name_match.group(1).strip()
            if len(candidate) > 2 and candidate not in ("SOA", "SBI", "HDFC", "ICICI", "AXIS", "STMT"):
                result["owner_name"] = candidate.title()

    # Period from/to from filename (e.g. "23-11-2024to26-11-2025")
    if not result.get("period_from"):
        period_match = re.search(
            r"(\d{2}[-_]\d{2}[-_]\d{4})[_\-\s]?to[_\-\s]?(\d{2}[-_]\d{2}[-_]\d{4})",
            filename, re.IGNORECASE
        )
        if period_match:
            def norm_date(s):
                s = s.replace("_", "-")
                for fmt in ["%d-%m-%Y", "%Y-%m-%d"]:
                    try:
                        return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
                    except ValueError:
                        continue
                return s
            result["period_from"] = norm_date(period_match.group(1))
            result["period_to"]   = norm_date(period_match.group(2))

    # Compute period from transactions if still missing
    if not result.get("period_from") and result.get("transactions"):
        dates = []
        for t in result["transactions"]:
            try:
                dates.append(datetime.strptime(str(t.get("date", ""))[:10], "%Y-%m-%d"))
            except ValueError:
                continue
        if dates:
            result["period_from"] = min(dates).strftime("%Y-%m-%d")
            result["period_to"]   = max(dates).strftime("%Y-%m-%d")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# MASTER CLEAN FUNCTION — called by upload route
# ─────────────────────────────────────────────────────────────────────────────

def clean_statement(statement: dict) -> dict:
    """
    Full cleaning pipeline for one parsed statement.
    Run this immediately after parsing, before storing to DB.

    Steps:
    1. Remove duplicates
    2. Extract/enrich header fields
    3. Run pre-credit balance audit
    4. Run FIFO audit
    5. Attach audit results to statement

    Returns enriched statement dict with audit_results attached.
    """
    txns = statement.get("transactions", [])

    # Step 1: Remove duplicates
    txns, dupes_removed = remove_duplicates(txns)
    statement = dict(statement)
    statement["transactions"] = txns

    # Step 2: Enrich header fields
    statement = extract_header_fields(statement)

    # Step 3 & 4: Audits
    pre_credit_result = pre_credit_balance_audit(txns)
    fifo_result       = fifo_audit(txns)

    # Step 5: Attach
    statement["audit_results"] = {
        "duplicates_removed": dupes_removed,
        "pre_credit_audit":   pre_credit_result,
        "fifo_audit":         fifo_result,
    }

    # Summary stats (used by /summary endpoint and P3 dashboard cards)
    success_txns   = [t for t in txns if t.get("status") == "SUCCESS"]
    failed_txns    = [t for t in txns if t.get("status") == "FAILED"]
    reversal_txns  = [t for t in txns if t.get("status") == "REVERSAL"]
    debit_txns     = [t for t in success_txns if t.get("txn_type") == "DEBIT"]
    credit_txns    = [t for t in success_txns if t.get("txn_type") == "CREDIT"]

    cash_withdrawals   = [t for t in debit_txns if any(
        kw in t.get("particulars", "").upper()
        for kw in ["CASH", "ATM", "CWDR", "CASH WDL", "CASH DEPOSIT BY", "CASH WITHDRAWAL"]
    )]
    cheque_withdrawals = [t for t in debit_txns if any(
        kw in t.get("particulars", "").upper()
        for kw in ["CHQ", "CHEQUE", "CTS", "CLEARING"]
    )]

    statement["summary_stats"] = {
        "total_transactions":      len(txns),
        "success_count":           len(success_txns),
        "failed_count":            len(failed_txns),
        "reversal_count":          len(reversal_txns),
        "total_debit":             round(sum(t.get("debit", 0) or 0 for t in success_txns), 2),
        "total_credit":            round(sum(t.get("credit", 0) or 0 for t in success_txns), 2),
        "net_flow":                round(
            sum(t.get("credit", 0) or 0 for t in success_txns) -
            sum(t.get("debit",  0) or 0 for t in success_txns), 2
        ),
        "cash_withdrawal_count":   len(cash_withdrawals),
        "cash_withdrawal_total":   round(sum(t.get("debit", 0) or 0 for t in cash_withdrawals), 2),
        "cheque_withdrawal_count": len(cheque_withdrawals),
        "cheque_withdrawal_total": round(sum(t.get("debit", 0) or 0 for t in cheque_withdrawals), 2),
        "balance_audit_clean":     pre_credit_result["is_clean"],
        "fifo_audit_clean":        fifo_result["is_clean"],
        "balance_mismatches":      pre_credit_result["mismatch_count"],
        "unsourced_debits":        fifo_result["unsourced_count"],
    }

    logger.info(
        f"clean_statement: {statement['account_number']} | "
        f"{len(txns)} txns | dupes={dupes_removed} | "
        f"bal_mismatches={pre_credit_result['mismatch_count']} | "
        f"unsourced={fifo_result['unsourced_count']}"
    )

    return statement
