"""
pdf_parser.py — PDF Text Extraction Parser (No OCR)
Handles bank statements that have selectable/copyable text in the PDF.
Supports: HDFC, SBI, ICICI, Axis, Kotak, YES Bank, PNB, Canara, BOB, IndusInd.

Strategy:
1. Extract all tables from every page using pdfplumber.
2. Find the header row (Date / Particulars / Debit / Credit / Balance keywords).
3. Normalize columns dynamically regardless of bank format.
4. Clean and classify every transaction row.
"""

import pdfplumber
import pandas as pd
import re
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# COLUMN KEYWORD MAPS (bank-agnostic matching)
# ─────────────────────────────────────────────
DATE_KEYWORDS = ["date", "txn date", "value date", "transaction date", "posting date"]
PARTICULARS_KEYWORDS = ["particulars", "description", "narration", "remarks", "details", "transaction details"]
DEBIT_KEYWORDS = ["debit", "withdrawal", "withdrawals", "dr", "debit amount", "amount (dr)"]
CREDIT_KEYWORDS = ["credit", "deposit", "deposits", "cr", "credit amount", "amount (cr)"]
BALANCE_KEYWORDS = ["balance", "closing balance", "running balance", "available balance"]
REF_KEYWORDS = ["chq/ref", "chq no", "ref no", "reference", "cheque no", "utr", "ref number"]

# Failed / Reversal markers in particulars text
FAILED_MARKERS = ["failed", "failure", "reversed", "reversal", "returned", "bounce", "bounced", "neft ret", "neft return", "rtn", "reject", "rejected"]
REVERSAL_MARKERS = ["reversal", "reversed", "rev-", "rev ", "return", "returned"]

# Common date formats across Indian banks
DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y",
    "%d/%m/%y", "%d-%m-%y", "%d %B %Y", "%Y-%m-%d",
    "%d.%m.%Y", "%d.%m.%y",
]


def _normalize_header(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", str(text).lower().strip())


def _match_column(header: str, keywords: list) -> bool:
    h = _normalize_header(header)
    return any(kw in h for kw in keywords)


def _parse_date(date_str: str) -> Optional[str]:
    """Try all known date formats. Return ISO YYYY-MM-DD or None."""
    if not date_str or str(date_str).strip() in ["", "nan", "None"]:
        return None
    raw = str(date_str).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try to extract date pattern from mixed strings like "22 Jun 2026 IST"
    match = re.search(r"(\d{1,2}[\s\-/]\w{3,9}[\s\-/]\d{2,4})", raw)
    if match:
        for fmt in ["%d %b %Y", "%d-%b-%Y", "%d %B %Y"]:
            try:
                return datetime.strptime(match.group(1), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return raw  # Return raw if unparseable — warn later


def _parse_amount(val) -> float:
    """Clean currency strings like '1,23,456.78' or '₹5,000' to float."""
    if val is None or str(val).strip() in ["", "nan", "None", "-", "--"]:
        return 0.0
    raw = str(val).strip()
    raw = re.sub(r"[₹$,\s]", "", raw)
    raw = re.sub(r"[^\d.\-]", "", raw)
    try:
        return abs(float(raw))  # Always positive; txn_type handles direction
    except ValueError:
        return 0.0


def _detect_status(particulars: str) -> str:
    """Classify transaction as SUCCESS / FAILED / REVERSAL from particulars text."""
    p = particulars.lower()
    if any(marker in p for marker in REVERSAL_MARKERS):
        return "REVERSAL"
    if any(marker in p for marker in FAILED_MARKERS):
        return "FAILED"
    return "SUCCESS"


def _extract_ref_number(particulars: str) -> Optional[str]:
    """Pull UPI ref, NEFT UTR, cheque numbers from particulars."""
    patterns = [
        r"\b(\d{12,22})\b",           # UPI / NEFT UTR (12-22 digit)
        r"ref\s*[:\-]?\s*(\w+)",       # REF: XXXX
        r"utr\s*[:\-]?\s*(\w+)",       # UTR: XXXX
        r"chq\s*[:\-]?\s*(\d+)",       # CHQ: XXXX
    ]
    for pattern in patterns:
        match = re.search(pattern, particulars.lower())
        if match:
            return match.group(1)
    return None


def _find_header_row(rows: list) -> Tuple[Optional[int], Optional[dict]]:
    """
    Scan rows to find the one that contains transaction column headers.
    Returns (row_index, column_map) where column_map = {
        'date': col_idx, 'particulars': col_idx, 'debit': col_idx, ...
    }
    PASS 1: exact keyword match (fast path, existing behavior unchanged).
    PASS 2 (Day 5 edge case hardening): fuzzy match if pass 1 finds nothing —
    catches typos like "Balanace" or unusual phrasing in unfamiliar bank formats.
    """
    # PASS 1: exact match (original logic, unchanged)
    for row_idx, row in enumerate(rows):
        if row is None:
            continue
        row_text = [str(cell).strip() if cell else "" for cell in row]
        
        found_date = any(_match_column(c, DATE_KEYWORDS) for c in row_text)
        found_balance = any(_match_column(c, BALANCE_KEYWORDS) for c in row_text)
        
        if found_date and found_balance:
            col_map = {}
            for col_idx, cell in enumerate(row_text):
                if _match_column(cell, DATE_KEYWORDS) and "date" not in col_map:
                    col_map["date"] = col_idx
                elif _match_column(cell, PARTICULARS_KEYWORDS) and "particulars" not in col_map:
                    col_map["particulars"] = col_idx
                elif _match_column(cell, DEBIT_KEYWORDS) and "debit" not in col_map:
                    col_map["debit"] = col_idx
                elif _match_column(cell, CREDIT_KEYWORDS) and "credit" not in col_map:
                    col_map["credit"] = col_idx
                elif _match_column(cell, BALANCE_KEYWORDS) and "balance" not in col_map:
                    col_map["balance"] = col_idx
                elif _match_column(cell, REF_KEYWORDS) and "ref" not in col_map:
                    col_map["ref"] = col_idx
            
            if "date" in col_map and "balance" in col_map:
                return row_idx, col_map

    # PASS 2: fuzzy match fallback (Day 5 edge case hardening)
    try:
        from app.parsers.edge_cases import (
            fuzzy_match_header, EXTENDED_DATE_KEYWORDS, EXTENDED_PARTICULARS_KEYWORDS,
            EXTENDED_DEBIT_KEYWORDS, EXTENDED_CREDIT_KEYWORDS, EXTENDED_BALANCE_KEYWORDS,
            detect_amount_type_layout,
        )
        for row_idx, row in enumerate(rows):
            if row is None:
                continue
            row_text = [str(cell).strip() if cell else "" for cell in row]

            found_date = any(fuzzy_match_header(c, EXTENDED_DATE_KEYWORDS) for c in row_text)
            found_balance = any(fuzzy_match_header(c, EXTENDED_BALANCE_KEYWORDS) for c in row_text)

            if found_date and found_balance:
                col_map = {}
                for col_idx, cell in enumerate(row_text):
                    if fuzzy_match_header(cell, EXTENDED_DATE_KEYWORDS) and "date" not in col_map:
                        col_map["date"] = col_idx
                    elif fuzzy_match_header(cell, EXTENDED_PARTICULARS_KEYWORDS) and "particulars" not in col_map:
                        col_map["particulars"] = col_idx
                    elif fuzzy_match_header(cell, EXTENDED_DEBIT_KEYWORDS) and "debit" not in col_map:
                        col_map["debit"] = col_idx
                    elif fuzzy_match_header(cell, EXTENDED_CREDIT_KEYWORDS) and "credit" not in col_map:
                        col_map["credit"] = col_idx
                    elif fuzzy_match_header(cell, EXTENDED_BALANCE_KEYWORDS) and "balance" not in col_map:
                        col_map["balance"] = col_idx

                # Check for single Amount+Type column layout
                amount_type = detect_amount_type_layout(row_text)
                if amount_type and "debit" not in col_map and "credit" not in col_map:
                    col_map["amount"] = amount_type["amount_col"]
                    col_map["type"] = amount_type["type_col"]

                if "date" in col_map and "balance" in col_map:
                    logger.info(f"Header found via FUZZY match at row {row_idx}: {col_map}")
                    return row_idx, col_map
    except ImportError:
        pass

    return None, None


def _extract_metadata_from_text(full_text: str) -> dict:
    """
    Extract account number, owner name, bank name, IFSC, branch, email
    from the free-form text at the top of the PDF (before the table).
    """
    meta = {
        "account_number": "UNKNOWN",
        "owner_name": "UNKNOWN",
        "bank_name": "UNKNOWN",
        "branch": None,
        "ifsc": None,
        "email": None,
        "period_from": None,
        "period_to": None,
        "opening_balance": None,
    }

    # Account number
    acc_patterns = [
        r"account\s*(?:number|no\.?|#)\s*[:\-]?\s*(\d[\d\s]{8,20})",
        r"a/c\s*(?:no\.?)?\s*[:\-]?\s*(\d[\d\s]{8,20})",
        r"acc(?:ount)?\s*#?\s*[:\-]?\s*(\d[\d\s]{8,20})",
    ]
    for p in acc_patterns:
        m = re.search(p, full_text, re.IGNORECASE)
        if m:
            meta["account_number"] = re.sub(r"\s+", "", m.group(1))
            break

    # IFSC
    m = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", full_text)
    if m:
        meta["ifsc"] = m.group(1)

    # Email
    m = re.search(r"[\w.\-]+@[\w.\-]+\.\w{2,}", full_text)
    if m:
        meta["email"] = m.group(0)

    # Bank name from common patterns — search ONLY first 600 chars to avoid
    # false matches from transaction narrations (e.g. "HDFC" in UPI to HDFC customer)
    full_text = full_text[:600]
    bank_names = {
        "idfc first": "IDFC First Bank",
        "idfc": "IDFC First Bank",
        "idfb": "IDFC First Bank",
        "bank of india": "Bank of India",
        "punjab national bank": "Punjab National Bank",
        "hdfc": "HDFC Bank",
        "sbi": "State Bank of India",
        "icici": "ICICI Bank",
        "axis": "Axis Bank",
        "kotak": "Kotak Mahindra Bank",
        "yes bank": "YES Bank",
        "pnb": "Punjab National Bank",
        "canara": "Canara Bank",
        "bank of baroda": "Bank of Baroda",
        "bob": "Bank of Baroda",
        "indusind": "IndusInd Bank",
        "union bank": "Union Bank of India",
        "idbi": "IDBI Bank",
        "federal bank": "Federal Bank",
    }
    text_lower = full_text.lower()
    for keyword, name in bank_names.items():
        if keyword in text_lower:
            meta["bank_name"] = name
            break

    # Statement period
    period_match = re.search(
        r"(?:from|period)[:\s]+(\d{1,2}[\w\s,/\-]+\d{4})\s*(?:to|–|-)\s*(\d{1,2}[\w\s,/\-]+\d{4})",
        full_text, re.IGNORECASE
    )
    if period_match:
        meta["period_from"] = _parse_date(period_match.group(1).strip())
        meta["period_to"] = _parse_date(period_match.group(2).strip())

    # Opening balance
    ob_match = re.search(r"opening\s*balance[:\s]+(?:inr\s*)?([\d,]+\.?\d*)", full_text, re.IGNORECASE)
    if ob_match:
        meta["opening_balance"] = _parse_amount(ob_match.group(1))

    # Owner name — typically after "Name:" or first capitalized line
    name_match = re.search(r"(?:name|account\s*holder)[:\s]+([A-Z][A-Za-z\s]{3,50})", full_text,re.IGNORECASE)
    if name_match:
        meta["owner_name"] = name_match.group(1).strip()

    return meta


def parse_pdf_text(file_path: str) -> dict:
    """
    Main entry: parse a bank statement PDF using pdfplumber (text-based).
    Returns a dict matching the BankStatement schema.
    Raises: ValueError if file unreadable or no transaction table found.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    transactions = []
    warnings = []
    all_rows = []
    full_text = ""

    with pdfplumber.open(str(path)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract full text for metadata (first page only for speed)
            if page_num == 0:
                full_text = page.extract_text() or ""

            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                if table:
                    all_rows.extend(table)

    if not all_rows:
        raise ValueError("No tables found in PDF. File may be scanned. Use OCR parser instead.")

    # Day 5: forward-fill merged cells before header detection
    try:
        from app.parsers.edge_cases import fill_merged_cells
        all_rows = fill_merged_cells(all_rows)
    except ImportError:
        pass

    # Find header row
    header_idx, col_map = _find_header_row(all_rows)
    if header_idx is None:
        raise ValueError("Could not find transaction header row (Date/Balance columns missing).")

    # Extract metadata
    meta = _extract_metadata_from_text(full_text)

    # Parse transaction rows (everything after the header)
    data_rows = all_rows[header_idx + 1:]
    row_index = 0

    for row in data_rows:
        if row is None:
            continue

        row_cells = [str(cell).strip() if cell else "" for cell in row]

        # Skip empty rows or summary/footer rows
        if not any(row_cells):
            continue
        if any(kw in " ".join(row_cells).lower() for kw in ["total", "opening balance", "closing balance", "statement generated"]):
            # Extract closing balance if present
            if "closing balance" in " ".join(row_cells).lower():
                for cell in row_cells:
                    val = _parse_amount(cell)
                    if val > 0:
                        meta["closing_balance"] = val
                        break
            continue

        # Get cell values by column map
        def get_col(key, default=""):
            idx = col_map.get(key)
            if idx is not None and idx < len(row_cells):
                return row_cells[idx]
            return default

        date_raw = get_col("date")
        particulars = get_col("particulars")
        debit_raw = get_col("debit")
        credit_raw = get_col("credit")
        balance_raw = get_col("balance")
        ref_raw = get_col("ref")

        # Skip rows with no date and no balance (continuation rows)
        parsed_date = _parse_date(date_raw)
        if not parsed_date and not balance_raw:
            # This might be a continuation of the previous particulars — append it
            if transactions:
                transactions[-1]["particulars"] += " " + particulars
            continue

        debit = _parse_amount(debit_raw)
        credit = _parse_amount(credit_raw)
        balance = _parse_amount(balance_raw)

        # Determine txn_type
        if debit > 0 and credit == 0:
            txn_type = "DEBIT"
        elif credit > 0 and debit == 0:
            txn_type = "CREDIT"
        elif debit > 0 and credit > 0:
            txn_type = "DEBIT"  # Edge case: take the larger
            warnings.append(f"Row {row_index}: Both debit and credit non-zero. Defaulting to DEBIT.")
        else:
            txn_type = "UNKNOWN"
            warnings.append(f"Row {row_index}: Zero debit and credit. Flagged as UNKNOWN.")

        status = _detect_status(particulars)
        ref_number = ref_raw if ref_raw else _extract_ref_number(particulars)

        txn_id = f"{meta['account_number']}_{row_index:04d}"

        transactions.append({
            "txn_id": txn_id,
            "date": parsed_date or date_raw,
            "particulars": particulars,
            "debit": debit,
            "credit": credit,
            "balance": balance,
            "txn_type": txn_type,
            "status": status,
            "ref_number": ref_number if ref_number else None,
            "raw_row_index": row_index,
        })
        row_index += 1

    if not transactions:
        raise ValueError("Header found but no transaction rows were extracted. Check PDF format.")

    logger.info(f"Parsed {len(transactions)} transactions from {path.name}. Warnings: {len(warnings)}")

    return {
        "account_number": meta["account_number"],
        "bank_name": meta["bank_name"],
        "owner_name": meta["owner_name"],
        "branch": meta.get("branch"),
        "ifsc": meta.get("ifsc"),
        "email": meta.get("email"),
        "period_from": meta.get("period_from"),
        "period_to": meta.get("period_to"),
        "opening_balance": meta.get("opening_balance"),
        "closing_balance": meta.get("closing_balance"),
        "source_file": path.name,
        "parse_method": "pdf_text",
        "transactions": transactions,
        "parse_warnings": warnings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL BANK FORMAT HANDLERS (added Day 2 after seeing real data)
# ─────────────────────────────────────────────────────────────────────────────

def _is_cbs_ledger(full_text: str) -> bool:
    """Detect PNB / Bank of India CBS ledger format (REP27/REP31)."""
    markers = ["customer account ledger", "rep27", "rep31", "gl. date", "gl sub head",
               "transaction details page", "service outlet"]
    text_lower = full_text.lower()
    return sum(1 for m in markers if m in text_lower) >= 2


def _is_idfc_first(full_text: str) -> bool:
    """Detect IDFC First Bank statement format."""
    return "idfc first bank" in full_text.lower() or "idfb" in full_text.lower()


def _parse_amount_with_cr_dr(val_str: str):
    """
    Parse amounts like '7,50,000.00Cr' or '74,082.00Cr' or '0.00'.
    Returns (amount, 'CR'|'DR'|None)
    """
    if not val_str or str(val_str).strip() in ["", "nan"]:
        return 0.0, None
    raw = str(val_str).strip()
    suffix = None
    if raw.upper().endswith("CR"):
        suffix = "CR"
        raw = raw[:-2]
    elif raw.upper().endswith("DR"):
        suffix = "DR"
        raw = raw[:-2]
    raw = re.sub(r"[₹$,\s]", "", raw)
    raw = re.sub(r"[^\d.\-]", "", raw)
    try:
        return abs(float(raw)), suffix
    except ValueError:
        return 0.0, suffix


def parse_cbs_ledger(file_path: str) -> dict:
    """
    Parse PNB / Bank of India CBS ledger PDFs (REP27 / REP31 format).
    Column layout: GL Date | Value Date | Instrument No | Particulars |
                   Debit Amount | Credit Amount | Balance | Entry User | Verified User
    Balance has Cr/Dr suffix. Account number is in the text.
    """
    path = Path(file_path)
    all_rows = []
    full_text = ""

    with pdfplumber.open(str(path)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num == 0:
                full_text = page.extract_text() or ""
            tables = page.extract_tables()
            for table in tables:
                if table:
                    all_rows.extend(table)

    # Extract account info from text
    meta = _extract_metadata_from_text(full_text)

    # CBS format: find rows where col[0] looks like a date (DD-MM-YYYY)
    transactions = []
    warnings     = []
    row_index    = 0
    DATE_RE      = re.compile(r"^\d{2}-\d{2}-\d{4}$")

    for row in all_rows:
        if not row or not row[0]:
            continue
        date_raw = str(row[0]).strip()
        if not DATE_RE.match(date_raw):
            continue

        # CBS cols: 0=GL_Date 1=Value_Date 2=Instrument 3=Particulars 4=Debit 5=Credit 6=Balance
        particulars = str(row[3]).strip() if len(row) > 3 else ""
        debit_raw   = str(row[4]).strip() if len(row) > 4 else ""
        credit_raw  = str(row[5]).strip() if len(row) > 5 else ""
        balance_raw = str(row[6]).strip() if len(row) > 6 else ""

        # Some CBS PDFs merge cols — try to find balance by Cr/Dr suffix
        if not balance_raw or balance_raw in ["", "nan"]:
            for cell in reversed(row):
                cell_str = str(cell or "").strip()
                if cell_str.upper().endswith("CR") or cell_str.upper().endswith("DR"):
                    balance_raw = cell_str
                    break

        debit,   _    = _parse_amount_with_cr_dr(debit_raw)
        credit,  _    = _parse_amount_with_cr_dr(credit_raw)
        balance, b_sfx = _parse_amount_with_cr_dr(balance_raw)

        parsed_date = _parse_date(date_raw)
        txn_type    = "DEBIT" if debit > 0 and credit == 0 else ("CREDIT" if credit > 0 else "UNKNOWN")
        status      = _detect_status(particulars)
        acc         = meta.get("account_number", "UNKNOWN")

        transactions.append({
            "txn_id":        f"{acc}_{row_index:04d}",
            "date":          parsed_date or date_raw,
            "particulars":   particulars,
            "debit":         debit,
            "credit":        credit,
            "balance":       balance,
            "txn_type":      txn_type,
            "status":        status,
            "ref_number":    _extract_ref_number(particulars),
            "raw_row_index": row_index,
        })
        row_index += 1

    logger.info(f"CBS ledger parse: {len(transactions)} transactions from {path.name}")
    return {
        "account_number":  meta.get("account_number", "UNKNOWN"),
        "bank_name":       meta.get("bank_name", "UNKNOWN"),
        "owner_name":      meta.get("owner_name", "UNKNOWN"),
        "branch":          meta.get("branch"),
        "ifsc":            meta.get("ifsc"),
        "email":           meta.get("email"),
        "period_from":     meta.get("period_from"),
        "period_to":       meta.get("period_to"),
        "opening_balance": meta.get("opening_balance"),
        "closing_balance": None,
        "source_file":     path.name,
        "parse_method":    "pdf_cbs_ledger",
        "transactions":    transactions,
        "parse_warnings":  [],
    }


def parse_idfc_first(file_path: str) -> dict:
    """
    Parse IDFC First Bank statements.
    pdfplumber extracts clean 7-column tables:
    [Trans Date and Time, Value Date, Transaction Details, Cheque No, Debit, Credit, Balance]
    Balance has 'Cr' suffix. Continuation rows have empty date+balance (merge into previous particulars).
    """
    path = Path(file_path)
    all_rows = []
    full_text = ""

    with pdfplumber.open(str(path)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num == 0:
                full_text = page.extract_text() or ""
            tables = page.extract_tables()
            for table in tables:
                if table:
                    all_rows.extend(table)

    meta = _extract_metadata_from_text(full_text)

    # Find header row: look for "Transaction Details" + "Balance" together
    header_idx = None
    for i, row in enumerate(all_rows):
        if not row:
            continue
        row_str = " ".join(str(c or "") for c in row).lower()
        if "transaction details" in row_str and "balance" in row_str:
            header_idx = i
            break

    if header_idx is None:
        return parse_pdf_text(file_path)

    transactions = []
    row_index    = 0
    DATETIME_RE  = re.compile(r"^\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}$")

    for row in all_rows[header_idx + 1:]:
        if not row:
            continue
        cells = [str(c or "").strip().replace("\n", " ") for c in row]
        while len(cells) < 7:
            cells.append("")

        trans_datetime = cells[0]
        value_date     = cells[1]
        particulars    = cells[2]
        cheque_no      = cells[3]
        debit_raw      = cells[4]
        credit_raw     = cells[5]
        balance_raw    = cells[6]

        if "opening balance" in particulars.lower():
            continue

        # Continuation row: no date in col 0 — append particulars to previous txn
        if not DATETIME_RE.match(trans_datetime):
            if transactions and particulars:
                transactions[-1]["particulars"] += " " + particulars
            continue

        debit,  _ = _parse_amount_with_cr_dr(debit_raw)
        credit, _ = _parse_amount_with_cr_dr(credit_raw)
        balance, _ = _parse_amount_with_cr_dr(balance_raw)

        txn_type = "DEBIT" if debit > 0 and credit == 0 else ("CREDIT" if credit > 0 else "UNKNOWN")
        status   = _detect_status(particulars)
        if "failed cr txn" in particulars.lower():
            status = "FAILED"

        # date format is DD/MM/YY — convert to DD/MM/YYYY for _parse_date
        date_part = value_date if value_date else trans_datetime.split()[0]
        parsed_date = _parse_date(date_part)

        acc = meta.get("account_number", "UNKNOWN")
        ref = cheque_no if cheque_no else _extract_ref_number(particulars)

        transactions.append({
            "txn_id":        f"{acc}_{row_index:04d}",
            "date":          parsed_date or date_part,
            "particulars":   particulars,
            "debit":         debit,
            "credit":        credit,
            "balance":       balance,
            "txn_type":      txn_type,
            "status":        status,
            "ref_number":    ref,
            "raw_row_index": row_index,
        })
        row_index += 1

    logger.info(f"IDFC First parse: {len(transactions)} transactions from {path.name}")
    return {
        "account_number":  meta.get("account_number", "UNKNOWN"),
        "bank_name":       "IDFC First Bank",
        "owner_name":      meta.get("owner_name", "UNKNOWN"),
        "branch":          meta.get("branch"),
        "ifsc":            meta.get("ifsc"),
        "email":           meta.get("email"),
        "period_from":     meta.get("period_from"),
        "period_to":       meta.get("period_to"),
        "opening_balance": 0.0,
        "closing_balance": None,
        "source_file":     path.name,
        "parse_method":    "pdf_idfc_first",
        "transactions":    transactions,
        "parse_warnings":  [],
    }

def parse_cbs_text_lines(file_path: str) -> dict:
    """
    Parse CBS Ledger PDFs (PNB REP31 / Bank of India REP27) using
    text-line extraction — pdfplumber tables don't work for these.

    TWO sub-formats detected:

    FORMAT A — PNB REP31 (DEVANSHU):
      Each transaction is a single line:
      DD-MM-YYYY DD-MM-YYYY PARTICULARS DEBIT_OR_CREDIT BALANCE[Cr]
      Where DEBIT vs CREDIT is determined by whether balance went up or down.
      Special: cheque/instrument numbers appear inline before particulars.

    FORMAT B — Bank of India REP27 (KOMAL):
      pdfplumber returns single-cell table rows like:
      "DD-MM-YYYYSREFERENCE PARTICULARS AMOUNT BALANCE[CR/DR]"
      Direction determined by /CR/ or /DR/ in UPI narration.
    """
    path = Path(file_path)
    full_text = ""
    all_lines = []

    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            full_text += page_text + "\n"
            # Also try single-cell table rows (BOI format)
            tables = page.extract_tables()
            for table in tables:
                for row in (table or []):
                    if row and row[0]:
                        cell = str(row[0]).strip()
                        if re.match(r'^\d{2}-\d{2}-\d{4}', cell) and len(cell) > 20:
                            all_lines.append(('TABLE', cell))

    # Add text lines
    for line in full_text.splitlines():
        line = line.strip()
        if re.match(r'^\d{2}-\d{2}-\d{4}', line) and len(line) > 20:
            all_lines.append(('TEXT', line))

    meta = _extract_metadata_from_text(full_text)

    # Extract account number from text (CBS format: "Acct Range : XXXX to XXXX")
    acc_range = re.search(r'acct range\s*:\s*(\d+)\s+to\s+\d+', full_text, re.IGNORECASE)
    if acc_range:
        meta['account_number'] = acc_range.group(1)

    acc_no_match = re.search(r'account\s+(?:number|no\.?)\s*[:/]?\s*(\d{8,20})', full_text, re.IGNORECASE)
    if acc_no_match:
        meta['account_number'] = acc_no_match.group(1).split('/')[0]

    # ── PNB REP31 regex ──────────────────────────────────────────────────────
    # DD-MM-YYYY DD-MM-YYYY [INSTRUMENT] PARTICULARS AMOUNT BALANCE[Cr] [USER USER]
    PNB_RE = re.compile(
        r'^(\d{2}-\d{2}-\d{4})\s+'          # GL date
        r'(\d{2}-\d{2}-\d{4})\s+'           # value date
        r'(.+?)\s+'                           # particulars (includes instrument if any)
        r'([\d,]+\.?\d*)\s+'                 # debit OR credit amount
        r'([\d,]+\.?\d*(?:Cr|Dr)?)\s*'      # running balance
        r'(?:\S+\s+\S+)?\s*$',              # optional user ids at end
        re.IGNORECASE
    )

    # ── BOI REP27 regex ──────────────────────────────────────────────────────
    # DDMMYYYYSREFERENCE PARTICULARS AMOUNT BALANCE[CR]
    BOI_RE = re.compile(
        r'^(\d{2}-\d{2}-\d{4})\s*'          # date
        r'(\S+)\s+'                           # tran ref (S + digits)
        r'(.+?)\s+'                           # particulars
        r'([\d,]+\.?\d*)\s+'                 # amount
        r'([\d,]+\.?\d*(?:CR|DR))\s*$',     # balance with CR/DR
        re.IGNORECASE
    )

    transactions = []
    warnings     = []
    row_index    = 0
    prev_balance = None
    seen_lines   = set()  # deduplicate TEXT vs TABLE extractions

    SKIP_PATTERNS = ['page total', 'closing balance', 'total credit', 'total debit',
                     'brought forward', 'order by', 'date limits', 'draw power']

    for source, line in all_lines:
        line_key = line[:80]
        if line_key in seen_lines:
            continue
        seen_lines.add(line_key)

        line_lower = line.lower()
        if any(skip in line_lower for skip in SKIP_PATTERNS):
            continue

        # Try BOI format first (has explicit CR/DR suffix on balance)
        m = BOI_RE.match(line)
        if m:
            date_raw, ref, particulars, amount_str, balance_str = m.groups()
            amount  = _parse_amount(amount_str)
            balance, b_sfx = _parse_amount_with_cr_dr(balance_str)
            parsed_date = _parse_date(date_raw)

            # Direction from narration
            p_up = particulars.upper()
            if '/CR/' in p_up or 'IMPS-IN' in p_up or 'NEFT CR' in p_up or 'UPI CR' in p_up:
                txn_type = 'CREDIT'; debit = 0.0; credit = amount
            elif '/DR/' in p_up or 'IMPS-OPW' in p_up or 'ATM' in p_up or 'WDL' in p_up:
                txn_type = 'DEBIT';  debit = amount; credit = 0.0
            else:
                # Infer from balance direction vs previous
                if prev_balance is not None:
                    txn_type = 'CREDIT' if balance > prev_balance else 'DEBIT'
                    debit   = 0.0 if txn_type == 'CREDIT' else amount
                    credit  = amount if txn_type == 'CREDIT' else 0.0
                else:
                    txn_type = 'UNKNOWN'; debit = 0.0; credit = 0.0

            prev_balance = balance
            status = _detect_status(particulars)
            acc    = meta.get('account_number', 'UNKNOWN')

            transactions.append({
                'txn_id': f'{acc}_{row_index:04d}',
                'date': parsed_date or date_raw,
                'particulars': particulars.strip(),
                'debit': debit, 'credit': credit, 'balance': balance,
                'txn_type': txn_type, 'status': status,
                'ref_number': ref, 'raw_row_index': row_index,
            })
            row_index += 1
            continue

        # Try PNB format
        m = PNB_RE.match(line)
        if m:
            date_raw, value_date, particulars, amount_str, balance_str = m.groups()
            # Skip limit detail lines (contain "0.00 0.00 2.5000")
            if re.match(r'^0\.00\s+0\.00\s+\d+\.\d{4}$', f"{amount_str} {balance_str}"):
                continue

            amount  = _parse_amount(amount_str)
            balance, b_sfx = _parse_amount_with_cr_dr(balance_str)
            parsed_date = _parse_date(date_raw)

            # PNB: infer direction from balance movement vs previous
            if prev_balance is not None:
                txn_type = 'CREDIT' if balance > prev_balance else 'DEBIT'
            else:
                # First txn — if particulars has NRTGS/NEFT/IMPS-IN → credit
                p_up = particulars.upper()
                if any(kw in p_up for kw in ['NRTGS', 'NEFT', 'IMPS-IN', 'UPI/P2A']):
                    txn_type = 'CREDIT'
                else:
                    txn_type = 'DEBIT'

            debit  = amount if txn_type == 'DEBIT'  else 0.0
            credit = amount if txn_type == 'CREDIT' else 0.0
            prev_balance = balance
            status = _detect_status(particulars)
            acc    = meta.get('account_number', 'UNKNOWN')

            transactions.append({
                'txn_id': f'{acc}_{row_index:04d}',
                'date': parsed_date or date_raw,
                'particulars': particulars.strip(),
                'debit': debit, 'credit': credit, 'balance': balance,
                'txn_type': txn_type, 'status': status,
                'ref_number': _extract_ref_number(particulars),
                'raw_row_index': row_index,
            })
            row_index += 1

    logger.info(f"CBS text-line parse: {len(transactions)} transactions from {path.name}")

    return {
        'account_number':  meta.get('account_number', 'UNKNOWN'),
        'bank_name':       meta.get('bank_name', 'UNKNOWN'),
        'owner_name':      meta.get('owner_name', 'UNKNOWN'),
        'branch':          meta.get('branch'),
        'ifsc':            meta.get('ifsc'),
        'email':           meta.get('email'),
        'period_from':     meta.get('period_from'),
        'period_to':       meta.get('period_to'),
        'opening_balance': meta.get('opening_balance'),
        'closing_balance': None,
        'source_file':     path.name,
        'parse_method':    'pdf_cbs_text',
        'transactions':    transactions,
        'parse_warnings':  warnings,
    }
