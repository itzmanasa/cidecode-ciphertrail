"""
transactions.py — GET /api/transactions and POST /api/audit
===========================================================
/api/transactions : returns cleaned transaction list from a parsed statement
/api/audit        : runs both balance audit modes on a statement
/api/summary      : returns summary stats + header fields (for P3 dashboard cards)
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from app.schemas import BankStatement
from app.utils.cleaner import (
    clean_statement,
    pre_credit_balance_audit,
    fifo_audit,
    remove_duplicates,
    extract_header_fields,
)

router = APIRouter()


class StatementRequest(BaseModel):
    statement: BankStatement


class MultiStatementRequest(BaseModel):
    statements: List[BankStatement]


# ── /api/transactions ─────────────────────────────────────────────────────────

@router.post("/transactions")
def get_transactions(body: StatementRequest):
    """
    Returns cleaned transaction list from a parsed statement.
    Removes duplicates, enriches header fields.
    P3 calls this to populate the transaction table.
    P2 calls this before inserting into DB.
    """
    stmt_dict = body.statement.model_dump()
    txns, dupes = remove_duplicates(stmt_dict.get("transactions", []))
    stmt_dict   = extract_header_fields(stmt_dict)

    # Separate by status for easy frontend rendering
    success   = [t for t in txns if t.get("status") == "SUCCESS"]
    failed    = [t for t in txns if t.get("status") == "FAILED"]
    reversals = [t for t in txns if t.get("status") == "REVERSAL"]

    return {
        "success": True,
        "account_number":    stmt_dict.get("account_number"),
        "bank_name":         stmt_dict.get("bank_name"),
        "owner_name":        stmt_dict.get("owner_name"),
        "period_from":       stmt_dict.get("period_from"),
        "period_to":         stmt_dict.get("period_to"),
        "duplicates_removed": dupes,
        "counts": {
            "total":    len(txns),
            "success":  len(success),
            "failed":   len(failed),
            "reversal": len(reversals),
        },
        "transactions": txns,         # All (for full table)
        "failed_transactions":    failed,     # Highlighted red in P3
        "reversal_transactions":  reversals,  # Highlighted yellow in P3
    }


# ── /api/audit ────────────────────────────────────────────────────────────────

@router.post("/audit")
def run_audit(body: StatementRequest):
    """
    Run both balance audit modes on a statement.
    Returns pre-credit audit + FIFO audit results.
    P3 uses this for the audit tab toggle (FIFO vs pre-credit).
    P2 stores these results in the anomalies table.
    """
    stmt_dict = body.statement.model_dump()
    txns      = stmt_dict.get("transactions", [])
    txns, _   = remove_duplicates(txns)

    pre_credit = pre_credit_balance_audit(txns)
    fifo       = fifo_audit(txns)

    return {
        "success":          True,
        "account_number":   stmt_dict.get("account_number"),
        "bank_name":        stmt_dict.get("bank_name"),
        "pre_credit_audit": pre_credit,
        "fifo_audit":       fifo,
        "overall_clean":    pre_credit["is_clean"] and fifo["is_clean"],
        "critical_findings": {
            "balance_mismatches": pre_credit["mismatch_count"],
            "unsourced_debits":   fifo["unsourced_count"],
            "excluded_from_audit": pre_credit.get("excluded_failed_reversal", 0),
        },
    }


# ── /api/summary ──────────────────────────────────────────────────────────────

@router.post("/summary")
def get_summary(body: StatementRequest):
    """
    Full clean + summary stats for one statement.
    P3 uses this to populate dashboard summary cards:
      - Total In / Total Out / Net Flow
      - Cash withdrawal count + total
      - Cheque withdrawal count + total
      - Balance audit status
      - Account header fields
    """
    stmt_dict = body.statement.model_dump()
    cleaned   = clean_statement(stmt_dict)

    return {
        "success":       True,
        "header": {
            "account_number": cleaned.get("account_number"),
            "bank_name":      cleaned.get("bank_name"),
            "owner_name":     cleaned.get("owner_name"),
            "branch":         cleaned.get("branch"),
            "ifsc":           cleaned.get("ifsc"),
            "email":          cleaned.get("email"),
            "period_from":    cleaned.get("period_from"),
            "period_to":      cleaned.get("period_to"),
            "opening_balance": cleaned.get("opening_balance"),
            "closing_balance": cleaned.get("closing_balance"),
        },
        "summary_stats":  cleaned.get("summary_stats", {}),
        "audit_results":  cleaned.get("audit_results", {}),
    }


# ── /api/clean ────────────────────────────────────────────────────────────────

@router.post("/clean")
def clean_and_return(body: StatementRequest):
    """
    Full pipeline: parse → deduplicate → enrich → audit → return.
    Single endpoint P2 can call to get everything in one shot before DB insert.
    """
    stmt_dict = body.statement.model_dump()
    cleaned   = clean_statement(stmt_dict)

    # Remove audit_results from transactions list to keep payload lean
    # Audit results are at top level
    return {
        "success":  True,
        "statement": {
            k: v for k, v in cleaned.items()
            if k != "audit_results"
        },
        "audit_results":  cleaned.get("audit_results", {}),
        "summary_stats":  cleaned.get("summary_stats", {}),
    }
