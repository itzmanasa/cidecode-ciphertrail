import sqlite3
import pandas as pd
import os

DB_PATH = "ciphertrail.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            txn_id TEXT,
            date TEXT,
            from_account TEXT,
            to_account TEXT,
            amount REAL,
            narration TEXT,
            is_reversal INTEGER DEFAULT 0,
            txn_type TEXT,
            debit REAL,
            credit REAL,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            account_id TEXT,
            holder_name TEXT,
            bank_name TEXT,
            branch TEXT,
            account_number TEXT,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            file_name TEXT,
            file_hash TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_transactions INTEGER,
            status TEXT DEFAULT 'processing'
        );

        CREATE TABLE IF NOT EXISTS custody_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            action TEXT,
            file_hash TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details TEXT
        );
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully")


def save_transactions(case_id: str, df: pd.DataFrame):
    """Saves a dataframe of transactions to SQLite."""
    conn = get_connection()

    df = df.copy()
    df["case_id"] = case_id
    df["date"] = df["date"].astype(str)
    df["is_reversal"] = df["is_reversal"].astype(int)

    # Only keep columns that exist in the transactions table —
    # adapter.py adds extra columns (debit, credit, balance, status, etc.)
    # that aren't part of this table's schema, so filter them out here.
    allowed_cols = ["case_id", "txn_id", "date", "from_account", "to_account",
                     "amount", "narration", "is_reversal", "txn_type", "debit", "credit", "status"  ]
    df_to_save = df[[c for c in allowed_cols if c in df.columns]]

    df_to_save.to_sql("transactions", conn, if_exists="append", index=False)
    conn.close()
    print(f"Saved {len(df_to_save)} transactions for case {case_id}")

def save_account_identity(case_id: str, statement: dict, file_name: str):
    """Persists account identity metadata so /analyse can return it."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO accounts (case_id, account_id, holder_name, bank_name, branch, account_number, email)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            case_id,
            statement.get("account_number", "UNKNOWN"),
            statement.get("owner_name", "UNKNOWN"),
            statement.get("bank_name", "UNKNOWN"),
            statement.get("branch"),
            statement.get("account_number", "UNKNOWN"),
            statement.get("email"),
        ),
    )
    conn.commit()
    conn.close()


def load_account_identity(case_id: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM accounts WHERE case_id = ? ORDER BY id DESC LIMIT 1", (case_id,)
    ).fetchone()
    conn.close()
    if not row:
        return {}
    return dict(row)

def save_account_identity(case_id: str, statement: dict, file_name: str):
    """Persists account identity metadata so /analyse can return it."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO accounts (case_id, account_id, holder_name, bank_name, branch, account_number, email)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            case_id,
            statement.get("account_number", "UNKNOWN"),
            statement.get("owner_name", "UNKNOWN"),
            statement.get("bank_name", "UNKNOWN"),
            statement.get("branch"),
            statement.get("account_number", "UNKNOWN"),
            statement.get("email"),
        ),
    )
    conn.commit()
    conn.close()


def load_account_identity(case_id: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM accounts WHERE case_id = ? ORDER BY id DESC LIMIT 1", (case_id,)
    ).fetchone()
    conn.close()
    if not row:
        return {}
    return dict(row)

def load_transactions(case_id: str) -> pd.DataFrame:
    """Loads transactions for a case from SQLite."""
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM transactions WHERE case_id = ?",
        conn,
        params=(case_id,)
    )
    conn.close()

    df["date"] = pd.to_datetime(df["date"])
    df["is_reversal"] = df["is_reversal"].astype(bool)
    df["amount"] = df["amount"].astype(float)

    return df


def save_case(case_id: str, file_name: str, file_hash: str, total_transactions: int):
    """Saves case metadata."""
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO cases (case_id, file_name, file_hash, total_transactions, status)
        VALUES (?, ?, ?, ?, 'complete')
    """, (case_id, file_name, file_hash, total_transactions))
    conn.commit()
    conn.close()


def log_custody(case_id: str, action: str, file_hash: str, details: str = ""):
    """Logs every action for chain of custody."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO custody_log (case_id, action, file_hash, details)
        VALUES (?, ?, ?, ?)
    """, (case_id, action, file_hash, details))
    conn.commit()
    conn.close()


def get_all_cases():
    """Returns list of all cases."""
    conn = get_connection()
    cases = pd.read_sql("SELECT * FROM cases ORDER BY upload_time DESC", conn)
    conn.close()
    return cases.to_dict(orient="records")


def clear_case(case_id: str):
    """Deletes all data for a case — for testing only."""
    conn = get_connection()
    conn.execute("DELETE FROM transactions WHERE case_id = ?", (case_id,))
    conn.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
    conn.execute("DELETE FROM custody_log WHERE case_id = ?", (case_id,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    init_db()

    from test_data import get_mock_transactions
    df = get_mock_transactions()

    case_id = "CASE_001"
    save_transactions(case_id, df)
    log_custody(case_id, "UPLOAD", "sha256_mock_hash_123", "Mock data uploaded for testing")
    save_case(case_id, "mock_bank_statement.pdf", "sha256_mock_hash_123", len(df))

    loaded_df = load_transactions(case_id)
    print(f"\nLoaded {len(loaded_df)} transactions from DB")
    print(loaded_df[["txn_id", "from_account", "to_account", "amount", "is_reversal"]])

    cases = get_all_cases()
    print(f"\nAll cases in DB:")
    for c in cases:
        print(f"  {c['case_id']} | {c['file_name']} | {c['total_transactions']} txns | {c['status']}")

    conn = get_connection()
    log = pd.read_sql("SELECT * FROM custody_log", conn)
    conn.close()
    print(f"\nCustody log:")
    print(log[["case_id", "action", "file_hash", "timestamp"]])