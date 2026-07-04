"""
analyse.py — POST /api/analyse
Accepts one or more already-parsed BankStatement JSON bodies,
runs reversal detection, returns anomaly report.

P3 calls this after uploading all statements.
P2 also calls analyze_reversals() internally after DB insert.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

from app.schemas import BankStatement
from app.utils.reversal_detector import analyze_reversals

router = APIRouter()


class AnalyseRequest(BaseModel):
    statements: List[BankStatement]


@router.post("/analyse")
def analyse_statements(body: AnalyseRequest):
    """
    Run reversal + anomaly detection on a list of parsed statements.
    Pass ALL uploaded statements together so cross-account matching works.
    """
    if not body.statements:
        return JSONResponse(status_code=400, content={"error": "No statements provided."})

    # Convert Pydantic models to plain dicts for the detector
    stmts_as_dicts = [s.model_dump() for s in body.statements]

    result = analyze_reversals(stmts_as_dicts)

    return {
        "success": True,
        "statements_analysed": len(body.statements),
        "anomaly_report": result,
    }
