"""
accounts.py — DB read routes (Day 4)
Lets P2 and P3 fetch persisted data without re-uploading files.
P2 specifically needs GET /api/accounts/all-transactions for cross-account graph building.
"""

from fastapi import APIRouter, HTTPException
from app.db.database import (
    get_all_accounts, get_account, get_transactions,
    get_all_transactions, get_audit_results, get_full_statement,
    delete_account,
)

router = APIRouter()


@router.get("/accounts")
def list_accounts():
    """List all uploaded accounts — P3 uses this for an account selector dropdown."""
    accounts = get_all_accounts()
    return {"success": True, "count": len(accounts), "accounts": accounts}


@router.get("/accounts/{account_number}")
def get_one_account(account_number: str):
    """Get full statement (header + transactions + audit) for one account."""
    stmt = get_full_statement(account_number)
    if not stmt:
        raise HTTPException(status_code=404, detail=f"Account {account_number} not found")
    return {"success": True, "statement": stmt}


@router.get("/accounts/{account_number}/transactions")
def get_account_transactions(account_number: str):
    """Just the transaction list for one account."""
    txns = get_transactions(account_number)
    if not txns:
        raise HTTPException(status_code=404, detail=f"No transactions found for {account_number}")
    return {"success": True, "account_number": account_number, "count": len(txns), "transactions": txns}


@router.get("/all-transactions")
def get_all_transactions_endpoint():
    """
    ALL transactions across ALL uploaded accounts.
    P2's graph engine calls this to build cross-account edges —
    this is the endpoint that makes round-trip detection (A→B→C→A) possible.
    """
    txns = get_all_transactions()
    accounts = {t["account_number"] for t in txns}
    return {
        "success": True,
        "total_transactions": len(txns),
        "account_count": len(accounts),
        "accounts": list(accounts),
        "transactions": txns,
    }


@router.delete("/accounts/{account_number}")
def remove_account(account_number: str):
    """Delete an account and its data — useful for re-testing during integration."""
    deleted = delete_account(account_number)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Account {account_number} not found")
    return {"success": True, "message": f"Deleted account {account_number}"}
