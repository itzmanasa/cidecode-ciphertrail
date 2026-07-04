"""
upload.py — POST /api/upload (Day 4: now persists to SQLite)
"""

import os
import uuid
import logging
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.parsers.dispatcher import dispatch_parse, SUPPORTED_EXTENSIONS
from app.schemas import BankStatement
from app.utils.cleaner import clean_statement
from app.db.database import save_statement

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "/tmp/forensic_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_statement(file: UploadFile = File(...)):
    """
    Upload a bank statement file.
    Parses → cleans → audits → SAVES TO SQLITE → returns full response.
    """
    suffix = os.path.splitext(file.filename)[-1].lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Accepted: {list(SUPPORTED_EXTENSIONS)}"
        )

    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")

    try:
        async with aiofiles.open(temp_path, "wb") as out:
            content = await file.read()
            await out.write(content)

        logger.info(f"Saved upload: {temp_path} ({len(content)} bytes)")

        result_dict = dispatch_parse(temp_path)
        result_dict["source_file"] = file.filename

        cleaned = clean_statement(result_dict)

        # Persist to SQLite
        account_number = save_statement(cleaned)

        stmt_fields = {k: v for k, v in cleaned.items()
                       if k not in ("audit_results", "summary_stats")}
        statement = BankStatement(**stmt_fields)

        return {
            "success": True,
            "message": (
                f"Parsed {len(statement.transactions)} transactions "
                f"via {statement.parse_method}. Saved to DB as account {account_number}."
            ),
            "statement":     statement,
            "summary_stats": cleaned.get("summary_stats", {}),
            "audit_results": cleaned.get("audit_results", {}),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Parse error: {e}")
        return {"success": False, "message": "Parse failed.", "error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {"success": False, "message": "Internal error.", "error": str(e)}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
