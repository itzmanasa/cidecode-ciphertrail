"""
registry.py — Parser Registry Pattern (Day 3 Morning)
======================================================
Every bank = one class inheriting BaseBankParser.
Same interface: parser.parse(file_path) → BankStatement dict.

Registry maps bank identifiers → parser class.
Dispatcher calls registry instead of hardcoded if/else.

Adding a new bank on hackathon day = add ONE class here. Nothing else changes.

Confirmed banks from real data:
  PDF  : IDFC First, PNB (CBS REP31), Bank of India (CBS REP27), HDFC, SBI, Axis, ICICI, Kotak
  XLS  : IndusInd, SBI
  XLSX : Generic (SBI CASA, IndusInd CASA)
  CSV  : Generic
"""

from abc import ABC, abstractmethod
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# BASE CLASS
# ─────────────────────────────────────────────────────────────────────────────

class BaseBankParser(ABC):
    """
    Every bank parser implements this interface.
    parse() must always return a dict matching BankStatement schema.
    Never raise — return parse_warnings instead for non-fatal issues.
    """

    bank_name: str = "UNKNOWN"
    supported_extensions: set = {".pdf", ".csv", ".xlsx", ".xls"}

    @abstractmethod
    def can_handle(self, file_path: str, peek_text: str = "") -> bool:
        """
        Return True if this parser can handle the given file.
        peek_text = first 600 chars of PDF text (empty for non-PDFs).
        """
        pass

    @abstractmethod
    def parse(self, file_path: str) -> dict:
        """Parse the file and return a BankStatement-compatible dict."""
        pass

    def _base_result(self, file_path: str, method: str) -> dict:
        """Skeleton result dict — fill in the fields in parse()."""
        return {
            "account_number":  "UNKNOWN",
            "bank_name":       self.bank_name,
            "owner_name":      "UNKNOWN",
            "branch":          None,
            "ifsc":            None,
            "email":           None,
            "period_from":     None,
            "period_to":       None,
            "opening_balance": None,
            "closing_balance": None,
            "source_file":     Path(file_path).name,
            "parse_method":    method,
            "transactions":    [],
            "parse_warnings":  [],
        }


# ─────────────────────────────────────────────────────────────────────────────
# CONCRETE PARSERS
# ─────────────────────────────────────────────────────────────────────────────

class IDFCFirstParser(BaseBankParser):
    bank_name = "IDFC First Bank"
    supported_extensions = {".pdf"}

    def can_handle(self, file_path: str, peek_text: str = "") -> bool:
        t = peek_text.lower()
        return "idfc first" in t or "idfb" in t or "idfc" in t

    def parse(self, file_path: str) -> dict:
        from app.parsers.pdf_parser import parse_idfc_first
        return parse_idfc_first(file_path)


class PNBCBSParser(BaseBankParser):
    bank_name = "Punjab National Bank"
    supported_extensions = {".pdf"}

    def can_handle(self, file_path: str, peek_text: str = "") -> bool:
        t = peek_text.lower()
        return ("punjab national bank" in t or "rep31" in t) and \
               ("customer account ledger" in t or "gl sub head" in t)

    def parse(self, file_path: str) -> dict:
        from app.parsers.pdf_parser import parse_cbs_text_lines
        return parse_cbs_text_lines(file_path)


class BankOfIndiaParser(BaseBankParser):
    bank_name = "Bank of India"
    supported_extensions = {".pdf"}

    def can_handle(self, file_path: str, peek_text: str = "") -> bool:
        t = peek_text.lower()
        return ("bank of india" in t or "rep27" in t) and \
               ("service outlet" in t or "tran ref num" in t)

    def parse(self, file_path: str) -> dict:
        from app.parsers.pdf_parser import parse_cbs_text_lines
        return parse_cbs_text_lines(file_path)


class BankOfMaharashtraParser(BaseBankParser):
    """BOM uses CBS format similar to PNB/BOI — same text-line parser works."""
    bank_name = "Bank of Maharashtra"
    supported_extensions = {".pdf"}

    def can_handle(self, file_path: str, peek_text: str = "") -> bool:
        t = peek_text.lower()
        return "bank of maharashtra" in t or "mahb" in t or \
               ("bom" in Path(file_path).name.lower() and "statement" in Path(file_path).name.lower())

    def parse(self, file_path: str) -> dict:
        from app.parsers.pdf_parser import parse_cbs_text_lines
        result = parse_cbs_text_lines(file_path)
        result["bank_name"] = "Bank of Maharashtra"
        return result


class IndusIndXLSParser(BaseBankParser):
    bank_name = "IndusInd Bank"
    supported_extensions = {".xls", ".xlsx"}

    def can_handle(self, file_path: str, peek_text: str = "") -> bool:
        ext = Path(file_path).suffix.lower()
        if ext not in self.supported_extensions:
            return False
        try:
            import xlrd
            wb = xlrd.open_workbook(file_path)
            sheet = wb.sheets()[0]
            if sheet.nrows >= 3:
                row2 = " ".join(str(sheet.cell_value(2, j)) for j in range(min(sheet.ncols, 20))).upper()
                return "TRAN DATE" in row2 and "PART TRAN TYPE" in row2
        except Exception:
            pass
        return False

    def parse(self, file_path: str) -> dict:
        from app.parsers.spreadsheet_parser import parse_xls
        return parse_xls(file_path)


class SBIXLSParser(BaseBankParser):
    bank_name = "State Bank of India"
    supported_extensions = {".xls", ".xlsx"}

    def can_handle(self, file_path: str, peek_text: str = "") -> bool:
        ext = Path(file_path).suffix.lower()
        if ext not in self.supported_extensions:
            return False
        try:
            import pandas as pd
            df = pd.read_excel(file_path, header=None, dtype=str, nrows=25)
            for i in range(len(df)):
                row_str = " ".join(str(v) for v in df.iloc[i].values if str(v) != "nan").lower()
                if "post date" in row_str and "description" in row_str:
                    return True
        except Exception:
            pass
        return False

    def parse(self, file_path: str) -> dict:
        from app.parsers.spreadsheet_parser import parse_xls
        return parse_xls(file_path)


class GenericPDFParser(BaseBankParser):
    """Fallback for HDFC, Axis, ICICI, Kotak, YES Bank — standard table layout."""
    bank_name = "UNKNOWN"
    supported_extensions = {".pdf"}

    # Bank name hints for enrichment
    BANK_HINTS = {
        "hdfc": "HDFC Bank",
        "icici": "ICICI Bank",
        "axis bank": "Axis Bank",
        "kotak": "Kotak Mahindra Bank",
        "yes bank": "YES Bank",
        "canara": "Canara Bank",
        "union bank": "Union Bank of India",
        "federal bank": "Federal Bank",
        "indusind": "IndusInd Bank",
        "paytm": "Paytm Payments Bank",
        "airtel": "Airtel Payments Bank",
    }

    def can_handle(self, file_path: str, peek_text: str = "") -> bool:
        return Path(file_path).suffix.lower() == ".pdf"

    def parse(self, file_path: str) -> dict:
        from app.parsers.pdf_parser import parse_pdf_text
        result = parse_pdf_text(file_path)
        # Enrich bank_name if still UNKNOWN
        if result.get("bank_name") == "UNKNOWN":
            t = (result.get("source_file", "") + " " + result.get("owner_name", "")).lower()
            for hint, name in self.BANK_HINTS.items():
                if hint in t:
                    result["bank_name"] = name
                    break
        return result


class GenericXLSXParser(BaseBankParser):
    bank_name = "UNKNOWN"
    supported_extensions = {".xlsx", ".xls", ".csv"}

    def can_handle(self, file_path: str, peek_text: str = "") -> bool:
        return Path(file_path).suffix.lower() in self.supported_extensions

    def parse(self, file_path: str) -> dict:
        ext = Path(file_path).suffix.lower()
        if ext == ".csv":
            from app.parsers.spreadsheet_parser import parse_csv
            return parse_csv(file_path)
        elif ext == ".xlsx":
            from app.parsers.spreadsheet_parser import parse_xlsx
            return parse_xlsx(file_path)
        else:
            from app.parsers.spreadsheet_parser import parse_xls
            return parse_xls(file_path)


class ImageOCRParser(BaseBankParser):
    bank_name = "UNKNOWN"
    supported_extensions = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}

    def can_handle(self, file_path: str, peek_text: str = "") -> bool:
        return Path(file_path).suffix.lower() in self.supported_extensions

    def parse(self, file_path: str) -> dict:
        from app.parsers.ocr_parser import parse_image_ocr
        return parse_image_ocr(file_path)


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

class ParserRegistry:
    """
    Ordered list of parsers. First one whose can_handle() returns True wins.
    Specific parsers must come BEFORE generic fallbacks.
    """

    def __init__(self):
        self._parsers: list[BaseBankParser] = [
            # PDF — specific first
            IDFCFirstParser(),
            PNBCBSParser(),
            BankOfIndiaParser(),
            BankOfMaharashtraParser(),
            # XLS/XLSX — specific first
            IndusIndXLSParser(),
            SBIXLSParser(),
            # Images
            ImageOCRParser(),
            # Generic fallbacks last
            GenericXLSXParser(),
            GenericPDFParser(),
        ]

    def get_parser(self, file_path: str, peek_text: str = "") -> BaseBankParser:
        """Return the first parser that can handle this file."""
        for parser in self._parsers:
            try:
                if Path(file_path).suffix.lower() in parser.supported_extensions:
                    if parser.can_handle(file_path, peek_text):
                        logger.info(f"Registry selected: {parser.__class__.__name__} for {Path(file_path).name}")
                        return parser
            except Exception as e:
                logger.warning(f"Parser {parser.__class__.__name__} can_handle() failed: {e}")
                continue

        # Should never reach here — GenericPDFParser/GenericXLSXParser always match
        raise ValueError(f"No parser found for {Path(file_path).name}")

    def list_parsers(self) -> list[str]:
        return [p.__class__.__name__ for p in self._parsers]


# Singleton instance — import this everywhere
registry = ParserRegistry()
