"""
schemas.py — Unified Transaction Schema
This is the SHARED CONTRACT between P1 (Parser), P2 (DB/Graph), and P3 (Frontend).
Everyone reads/writes using these exact models. Do NOT modify field names without
notifying the team — P2's DB columns and P3's frontend keys depend on this.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class TxnType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    UNKNOWN = "UNKNOWN"


class TxnStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVERSAL = "REVERSAL"
    UNKNOWN = "UNKNOWN"


class Transaction(BaseModel):
    """
    Represents a single bank transaction row.
    Maps directly to P2's `transactions` DB table.
    """
    txn_id: str = Field(..., description="Unique ID: {account_number}_{row_index}")
    date: str = Field(..., description="ISO format: YYYY-MM-DD")
    particulars: str = Field(..., description="Raw transaction description as-is from bank")
    debit: float = Field(default=0.0, description="Amount debited (outflow). 0 if credit.")
    credit: float = Field(default=0.0, description="Amount credited (inflow). 0 if debit.")
    balance: float = Field(..., description="Running balance after this transaction")
    txn_type: TxnType = Field(default=TxnType.UNKNOWN)
    status: TxnStatus = Field(default=TxnStatus.UNKNOWN)
    ref_number: Optional[str] = Field(default=None, description="Cheque no / UPI ref / NEFT ref")
    raw_row_index: Optional[int] = Field(default=None, description="Original row index in source file")


class BankStatement(BaseModel):
    """
    Top-level object returned by P1's parser.
    P2 stores this. P3 renders this.
    """
    account_number: str
    bank_name: str
    owner_name: str
    branch: Optional[str] = None
    ifsc: Optional[str] = None
    email: Optional[str] = None
    period_from: Optional[str] = None
    period_to: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    source_file: str = Field(..., description="Original filename uploaded")
    parse_method: str = Field(..., description="pdf_text | pdf_ocr | csv | xlsx | image_ocr")
    transactions: List[Transaction] = []
    parse_warnings: List[str] = Field(default=[], description="Non-fatal issues found during parsing")


class UploadResponse(BaseModel):
    """API response after file upload and parsing."""
    success: bool
    message: str
    statement: Optional[BankStatement] = None
    error: Optional[str] = None
