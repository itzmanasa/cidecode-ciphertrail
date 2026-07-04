"""
multi_upload.py — POST /api/upload-multi (Day 5 Evening)
============================================================
Accepts up to 5+ bank statement files in a single request, parses each,
merges them into one unified chronological timeline across all accounts.

This is what P2 needs for cross-account round-trip detection — instead of
calling /api/upload five times and manually combining results, P3/P2 can
send all files together and get back one merged, sorted, deduplicated view.

Each transaction in the merged timeline keeps its account_number so
graph-building (node=account, edge=transaction) works directly off this.
"""

import os
import uuid
import logging
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from app.parsers.dispatcher import dispatch_parse, SUPPORTED_EXTENSIONS
from app.schemas import BankStatement
from app.utils.cleaner import clean_statement
from app.db.database import save_statement

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "/tmp/forensic_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILES = 10  # Safety cap — hackathon brief says "5 bank statements" but allow headroom


@router.post("/upload-multi")
async def upload_multiple_statements(files: List[UploadFile] = File(...)):
    """
    Upload multiple bank statement files at once.
    Parses each, cleans each, saves each to DB, then returns:
      - individual per-account results (same shape as /api/upload)
      - ONE merged unified timeline sorted by date across all accounts

    This is the endpoint P2's graph engine and P3's "Money Flow" tab should call
    when working with multiple accounts together.
    """
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Max {MAX_FILES} files per request, got {len(files)}")
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")

    individual_results = []
    errors = []
    all_merged_txns = []

    for file in files:
        suffix = os.path.splitext(file.filename)[-1].lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            errors.append({"file": file.filename, "error": f"Unsupported type {suffix}"})
            continue

        temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")

        try:
            async with aiofiles.open(temp_path, "wb") as out:
                content = await file.read()
                await out.write(content)

            result_dict = dispatch_parse(temp_path)
            result_dict["source_file"] = file.filename
            cleaned = clean_statement(result_dict)
            account_number = save_statement(cleaned)

            stmt_fields = {k: v for k, v in cleaned.items()
                           if k not in ("audit_results", "summary_stats")}
            statement = BankStatement(**stmt_fields)

            individual_results.append({
                "file": file.filename,
                "success": True,
                "account_number": account_number,
                "transaction_count": len(statement.transactions),
                "summary_stats": cleaned.get("summary_stats", {}),
            })

            # Add to merged timeline — tag each txn with its source account
            for txn in cleaned.get("transactions", []):
                merged_txn = dict(txn)
                merged_txn["account_number"] = account_number
                merged_txn["bank_name"] = cleaned.get("bank_name")
                merged_txn["owner_name"] = cleaned.get("owner_name")
                all_merged_txns.append(merged_txn)

        except Exception as e:
            logger.exception(f"Failed to process {file.filename}: {e}")
            errors.append({"file": file.filename, "error": str(e)})
            individual_results.append({
                "file": file.filename,
                "success": False,
                "error": str(e),
            })
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # Build unified chronological timeline across all accounts
    def sort_key(t):
        try:
            from datetime import datetime
            return datetime.strptime(str(t.get("date", ""))[:10], "%Y-%m-%d")
        except ValueError:
            from datetime import datetime
            return datetime.max

    unified_timeline = sorted(all_merged_txns, key=sort_key)

    accounts_involved = list({t["account_number"] for t in all_merged_txns})

    return {
        "success": len(errors) == 0,
        "files_processed": len(files),
        "files_succeeded": len([r for r in individual_results if r.get("success")]),
        "files_failed": len(errors),
        "errors": errors,
        "individual_results": individual_results,
        "unified_timeline": {
            "total_transactions": len(unified_timeline),
            "accounts_involved": accounts_involved,
            "account_count": len(accounts_involved),
            "date_range": {
                "earliest": unified_timeline[0]["date"] if unified_timeline else None,
                "latest":   unified_timeline[-1]["date"] if unified_timeline else None,
            },
            "transactions": unified_timeline,
        },
    }
