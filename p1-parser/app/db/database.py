"""
database.py — SQLite Integration (Day 4)
==========================================
Lightweight persistence layer so P1's API doesn't lose data between requests.
P2 can also read directly from this SQLite file if her own DB setup has issues —
it's a guaranteed fallback that needs zero config.

Tables:
  accounts      — one row per uploaded statement (account-level metadata)
  transactions  — one row per transaction, linked to accounts via account_number
  audit_log     — stores audit results per account (JSON blob, simple and fast)

Design choice: JSON blobs for nested audit data instead of normalizing further —
this is a 7-day hackathon, not a banking core system. Speed over purity.
"""

import sqlite3
import json
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "forensic_audit.db"


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@contextmanager
def get_connection():
    """Context manager for SQLite connections — auto-commits, auto-closes."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist. Call once on app startup."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_number   TEXT PRIMARY KEY,
                bank_name        TEXT,
                owner_name       TEXT,
                branch           TEXT,
                ifsc             TEXT,
                email            TEXT,
                period_from      TEXT,
                period_to        TEXT,
                opening_balance  REAL,
                closing_balance  REAL,
                source_file      TEXT,
                parse_method     TEXT,
                uploaded_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS transactions (
                txn_id        TEXT PRIMARY KEY,
                account_number TEXT NOT NULL,
                date          TEXT,
                particulars   TEXT,
                debit         REAL DEFAULT 0,
                credit        REAL DEFAULT 0,
                balance       REAL,
                txn_type      TEXT,
                status        TEXT,
                ref_number    TEXT,
                raw_row_index INTEGER,
                FOREIGN KEY (account_number) REFERENCES accounts(account_number)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                account_number      TEXT PRIMARY KEY,
                summary_stats_json  TEXT,
                audit_results_json  TEXT,
                updated_at          TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (account_number) REFERENCES accounts(account_number)
            );

            CREATE INDEX IF NOT EXISTS idx_txn_account ON transactions(account_number);
            CREATE INDEX IF NOT EXISTS idx_txn_date    ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_txn_status  ON transactions(status);
        """)
    logger.info(f"Database initialized at {DB_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# WRITE OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

def save_statement(cleaned_statement: dict) -> str:
    """
    Save a cleaned BankStatement (with summary_stats + audit_results) to SQLite.
    Upserts: re-uploading the same account_number replaces old data.
    Returns the account_number that was saved.
    """
    acc = cleaned_statement.get("account_number", "UNKNOWN")

    with get_connection() as conn:
        # Upsert account
        conn.execute("""
            INSERT INTO accounts
                (account_number, bank_name, owner_name, branch, ifsc, email,
                 period_from, period_to, opening_balance, closing_balance,
                 source_file, parse_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_number) DO UPDATE SET
                bank_name=excluded.bank_name, owner_name=excluded.owner_name,
                branch=excluded.branch, ifsc=excluded.ifsc, email=excluded.email,
                period_from=excluded.period_from, period_to=excluded.period_to,
                opening_balance=excluded.opening_balance, closing_balance=excluded.closing_balance,
                source_file=excluded.source_file, parse_method=excluded.parse_method
        """, (
            acc, cleaned_statement.get("bank_name"), cleaned_statement.get("owner_name"),
            cleaned_statement.get("branch"), cleaned_statement.get("ifsc"), cleaned_statement.get("email"),
            cleaned_statement.get("period_from"), cleaned_statement.get("period_to"),
            cleaned_statement.get("opening_balance"), cleaned_statement.get("closing_balance"),
            cleaned_statement.get("source_file"), cleaned_statement.get("parse_method"),
        ))

        # Clear old transactions for this account before re-insert (handles re-upload)
        conn.execute("DELETE FROM transactions WHERE account_number = ?", (acc,))

        # Bulk insert transactions
        txns = cleaned_statement.get("transactions", [])
        conn.executemany("""
            INSERT OR REPLACE INTO transactions
                (txn_id, account_number, date, particulars, debit, credit,
                 balance, txn_type, status, ref_number, raw_row_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (t.get("txn_id"), acc, t.get("date"), t.get("particulars"),
             t.get("debit", 0), t.get("credit", 0), t.get("balance"),
             t.get("txn_type"), t.get("status"), t.get("ref_number"), t.get("raw_row_index"))
            for t in txns
        ])

        # Upsert audit log
        conn.execute("""
            INSERT INTO audit_log (account_number, summary_stats_json, audit_results_json, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(account_number) DO UPDATE SET
                summary_stats_json=excluded.summary_stats_json,
                audit_results_json=excluded.audit_results_json,
                updated_at=datetime('now')
        """, (
            acc,
            json.dumps(cleaned_statement.get("summary_stats", {})),
            json.dumps(cleaned_statement.get("audit_results", {})),
        ))

    logger.info(f"Saved statement for account {acc}: {len(cleaned_statement.get('transactions', []))} transactions")
    return acc


# ─────────────────────────────────────────────────────────────────────────────
# READ OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_account(account_number: str) -> Optional[dict]:
    """Fetch one account's header info."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE account_number = ?", (account_number,)
        ).fetchone()
        return dict(row) if row else None


def get_all_accounts() -> List[dict]:
    """List all uploaded accounts — used by P3 to show account selector."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM accounts ORDER BY uploaded_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_transactions(account_number: str) -> List[dict]:
    """Fetch all transactions for one account, sorted by date."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE account_number = ? ORDER BY date, raw_row_index",
            (account_number,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_transactions() -> List[dict]:
    """
    Fetch ALL transactions across ALL accounts.
    This is what P2's graph engine needs — cross-account edges require seeing everyone at once.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY account_number, date, raw_row_index"
        ).fetchall()
        return [dict(r) for r in rows]


def get_audit_results(account_number: str) -> Optional[dict]:
    """Fetch stored audit results for one account."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM audit_log WHERE account_number = ?", (account_number,)
        ).fetchone()
        if not row:
            return None
        return {
            "account_number":  row["account_number"],
            "summary_stats":   json.loads(row["summary_stats_json"]),
            "audit_results":   json.loads(row["audit_results_json"]),
            "updated_at":      row["updated_at"],
        }


def get_full_statement(account_number: str) -> Optional[dict]:
    """
    Reconstruct a full BankStatement dict (header + transactions + audit)
    from the DB — same shape as what /api/upload originally returned.
    Useful for P2/P3 to re-fetch without re-uploading the file.
    """
    account = get_account(account_number)
    if not account:
        return None

    transactions = get_transactions(account_number)
    audit = get_audit_results(account_number) or {}

    return {
        "account_number":  account["account_number"],
        "bank_name":       account["bank_name"],
        "owner_name":      account["owner_name"],
        "branch":          account["branch"],
        "ifsc":            account["ifsc"],
        "email":           account["email"],
        "period_from":     account["period_from"],
        "period_to":       account["period_to"],
        "opening_balance": account["opening_balance"],
        "closing_balance": account["closing_balance"],
        "source_file":     account["source_file"],
        "parse_method":    account["parse_method"],
        "transactions":    transactions,
        "summary_stats":   audit.get("summary_stats", {}),
        "audit_results":   audit.get("audit_results", {}),
    }


def delete_account(account_number: str) -> bool:
    """Remove an account and all its transactions. Used for re-testing/cleanup."""
    with get_connection() as conn:
        conn.execute("DELETE FROM transactions WHERE account_number = ?", (account_number,))
        conn.execute("DELETE FROM audit_log WHERE account_number = ?", (account_number,))
        cur = conn.execute("DELETE FROM accounts WHERE account_number = ?", (account_number,))
        return cur.rowcount > 0
