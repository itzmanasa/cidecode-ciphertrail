from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import hashlib
import uuid
import os
import requests
from database import get_connection
from pathlib import Path

from adapter import adapt_statement_to_engine
from findings import get_full_findings
from database import init_db, save_transactions, save_case, log_custody, load_transactions, get_all_cases

app = FastAPI(title="CipherTrail API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

P1_API = "http://localhost:8000"

init_db()


def hash_file(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _mock_statement(filename: str) -> dict:
    """Fallback mock when Person 1's API isn't available."""
    from test_data import get_mock_transactions
    df = get_mock_transactions()
    return {
        "account_number": "MOCK_1234",
        "bank_name": "Mock Bank",
        "owner_name": "Test User",
        "branch": None,
        "ifsc": None,
        "email": None,
        "period_from": None,
        "period_to": None,
        "opening_balance": None,
        "closing_balance": None,
        "source_file": filename,
        "parse_method": "mock",
        "transactions": [
            {
                "txn_id": row["txn_id"],
                "date": str(row["date"]),
                "particulars": row["narration"],
                "debit": row["amount"] if not row["is_reversal"] else 0,
                "credit": 0,
                "balance": 0,
                "txn_type": "DEBIT",
                "status": "REVERSAL" if row["is_reversal"] else "SUCCESS",
                "ref_number": None,
            }
            for _, row in df.iterrows()
        ],
        "parse_warnings": []
    }


@app.get("/")
def root():
    return {"status": "CipherTrail P2 API running", "version": "1.0.0"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    case_id = f"CASE_{uuid.uuid4().hex[:8].upper()}"
    file_path = UPLOAD_DIR / f"{case_id}_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_hash = hash_file(str(file_path))
    log_custody(case_id, "UPLOAD", file_hash, f"File: {file.filename}")

    audit = {}
    stats = {}

    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{P1_API}/api/upload",
                files={"file": (file.filename, f)},
                timeout=30
            )

        if response.status_code != 200:
            raise ValueError(f"Parser returned {response.status_code}: {response.text}")

        data = response.json()
        statement = data["statement"]
        audit = data.get("audit_results", {})
        stats = data.get("summary_stats", {})

        print(f"Parser success: {stats.get('total_transactions')} transactions")

    except Exception as e:
        print(f"Person 1 API failed: {e} — falling back to mock")
        statement = _mock_statement(file.filename)
        audit = {}
        stats = {}

    df = adapt_statement_to_engine(statement, case_id)

    if df.empty:
        raise HTTPException(status_code=400, detail="No transactions found in file.")

    save_transactions(case_id, df)
    save_case(case_id, file.filename, file_hash, len(df))
    log_custody(
        case_id, "PARSED", file_hash,
        f"{len(df)} transactions, {int(df['is_reversal'].sum())} reversals"
    )

    return {
        "success": True,
        "case_id": case_id,
        "file_name": file.filename,
        "file_hash": file_hash,
        "total_transactions": len(df),
        "reversals_found": int(df["is_reversal"].sum()),
        "account_id": df["account_id"].iloc[0] if "account_id" in df.columns else "UNKNOWN",
        "owner_name": statement.get("owner_name", "Unknown"),
        "bank_name": statement.get("bank_name", "Unknown"),
        "period_from": statement.get("period_from"),
        "period_to": statement.get("period_to"),
        "audit": {
            "duplicates_removed": audit.get("duplicates_removed", 0),
            "balance_audit_clean": stats.get("balance_audit_clean", True),
            "total_debit": stats.get("total_debit", 0),
            "total_credit": stats.get("total_credit", 0),
            "cash_withdrawal_count": stats.get("cash_withdrawal_count", 0),
            "cash_withdrawal_total": stats.get("cash_withdrawal_total", 0),
            "cheque_withdrawal_count": stats.get("cheque_withdrawal_count", 0),
            "cheque_withdrawal_total": stats.get("cheque_withdrawal_total", 0),
        }
    }


@app.get("/analyse/{case_id}")
def analyse(case_id: str):
    df = load_transactions(case_id)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    log_custody(case_id, "ANALYSE", "", "Full analysis triggered")
    results = get_full_findings(df)

    return {
        "success": True,
        "case_id": case_id,
        "findings": results
    }


@app.get("/cases")
def list_cases():
    return {"cases": get_all_cases()}


@app.get("/transactions/{case_id}")
def get_transactions(case_id: str):
    df = load_transactions(case_id)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    return {
        "case_id": case_id,
        "total": len(df),
        "transactions": df.to_dict(orient="records")
    }
@app.get("/certificate/{case_id}")
def get_certificate(case_id: str):
    """Generate Section 65B certificate for a case."""
    from section_65b import generate_65b_certificate
    from database import load_transactions

    df = load_transactions(case_id)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    conn = get_connection()
    import pandas as pd
    cases = pd.read_sql("SELECT * FROM cases WHERE case_id = ?", conn, params=(case_id,))
    conn.close()

    if cases.empty:
        raise HTTPException(status_code=404, detail=f"Case metadata not found.")

    case = cases.iloc[0]

    cert = generate_65b_certificate(
        case_id=case_id,
        file_path=case["file_name"],
        file_hash=case["file_hash"],
        account_number=df["account_id"].iloc[0] if "account_id" in df.columns else "UNKNOWN",
        bank_name=df["bank_name"].iloc[0] if "bank_name" in df.columns else "UNKNOWN",
        owner_name="Account Holder",
        total_transactions=int(case["total_transactions"]),
        reversal_count=int(df["is_reversal"].sum()),
        round_trip_count=0
    )

    return {"success": True, "case_id": case_id, "certificate": cert}


@app.get("/evidence-package/{case_id}")
def download_evidence_package(case_id: str):
    """Generate and return evidence ZIP package."""
    from fastapi.responses import FileResponse
    from evidence_package import create_evidence_package
    from findings import get_full_findings

    df = load_transactions(case_id)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    conn = get_connection()
    import pandas as pd
    cases = pd.read_sql("SELECT * FROM cases WHERE case_id = ?", conn, params=(case_id,))
    conn.close()

    case = cases.iloc[0]
    findings = get_full_findings(df)

    statement = {
        "account_number": df["account_id"].iloc[0] if "account_id" in df.columns else "UNKNOWN",
        "bank_name": df["bank_name"].iloc[0] if "bank_name" in df.columns else "UNKNOWN",
        "owner_name": "Account Holder"
    }

    zip_path = create_evidence_package(
        case_id=case_id,
        file_path=case["file_name"],
        file_hash=case["file_hash"],
        findings=findings,
        statement=statement
    )

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"evidence_{case_id}.zip"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)