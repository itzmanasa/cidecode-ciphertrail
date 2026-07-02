"""
spreadsheet_parser.py — CSV, XLSX, XLS Parser (Day 2 upgraded)
Handles confirmed real-world formats:
  - IndusInd Bank XLS (Excel serial dates, PART TRAN TYPE C/D column)
  - SBI XLS (header at row 20, \n\n in descriptions, DEP TFR/WDL TFR prefixes)
  - Generic CSV/XLSX (any bank with standard Date/Debit/Credit/Balance columns)
"""

import pandas as pd
import re
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── SBI-specific markers in Description ──────────────────────────────────────
SBI_CREDIT_PREFIXES = ["dep tfr", "cash deposit", "imps in", "neft cr", "upi/cr", "by transfer"]
SBI_DEBIT_PREFIXES  = ["wdl tfr", "cash wdl", "atm wdl", "imps out", "neft dr", "upi/dr", "to transfer", "atm/"]

FAILED_MARKERS   = ["failed", "failure", "reversed", "reversal", "returned", "bounce", "bounced",
                    "neft ret", "neft return", "rtn", "reject", "rejected"]
REVERSAL_MARKERS = ["reversal", "reversed", "rev-", "rev ", "return", "returned", "ft-rev"]


def _clean_description(text: str) -> str:
    """Strip embedded newlines and extra whitespace from SBI descriptions."""
    if not text or str(text) == 'nan':
        return ""
    return re.sub(r'\s+', ' ', str(text).replace('\n', ' ').replace('\r', ' ')).strip()


def _parse_amount(val) -> float:
    if val is None or str(val).strip() in ["", "nan", "None", "-", "--"]:
        return 0.0
    raw = re.sub(r"[₹$,\s]", "", str(val).strip())
    raw = re.sub(r"[^\d.\-]", "", raw)
    try:
        return abs(float(raw))
    except ValueError:
        return 0.0


def _parse_date_str(date_str: str) -> str:
    """Parse standard date strings to YYYY-MM-DD."""
    if not date_str or str(date_str).strip() in ["", "nan", "None"]:
        return None
    raw = str(date_str).strip()
    for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y",
                "%d-%m-%y", "%d/%m/%y", "%d.%m.%Y", "%d.%m.%y"]:
        try:
            return datetime.strptime(raw[:11], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _excel_serial_to_date(serial) -> str:
    """Convert Excel serial date number (e.g. 45783.0) to YYYY-MM-DD."""
    try:
        n = float(serial)
        if n < 1:
            return None
        # Excel epoch is 1900-01-01, but has leap year bug (counts 1900 as leap)
        epoch = datetime(1899, 12, 30)
        return (epoch + timedelta(days=n)).strftime("%Y-%m-%d")
    except Exception:
        return None


def _detect_status(particulars: str) -> str:
    p = particulars.lower()
    if any(m in p for m in REVERSAL_MARKERS):
        return "REVERSAL"
    if any(m in p for m in FAILED_MARKERS):
        return "FAILED"
    return "SUCCESS"


def _extract_ref(particulars: str):
    for pattern in [r"\b(\d{12,22})\b", r"ref\s*[:\-]?\s*(\w+)", r"utr\s*[:\-]?\s*(\w+)"]:
        m = re.search(pattern, particulars.lower())
        if m:
            return m.group(1)
    return None


# ── IndusInd XLS ──────────────────────────────────────────────────────────────

def _parse_indusind_xls(file_path: str) -> dict:
    """
    IndusInd format:
    Row 0: date range
    Row 2: headers — ACCOUNT NO | TRAN DATE | VALUE DATE | TRAN PARTICULAR |
                      INSTRUMENT NO | DEBIT AMOUNT | CREDIT AMOUNT | BALANCE AMOUNT |
                      BALANCE INDICATOR | ACCOUNT NAME | ... | PART TRAN TYPE | ...
    Rows 3+: data. Dates are Excel serial numbers.
    txn_type determined by PART TRAN TYPE col (C=CREDIT, D=DEBIT)
    """
    import xlrd
    wb   = xlrd.open_workbook(file_path)
    sheet = wb.sheets()[0]

    # Extract account name from row 3
    account_name = str(sheet.cell_value(3, 9)).strip() if sheet.nrows > 3 else "UNKNOWN"
    account_no   = str(sheet.cell_value(3, 0)).strip().split('.')[0] if sheet.nrows > 3 else "UNKNOWN"

    transactions = []
    warnings     = []

    for i in range(3, sheet.nrows):
        row = [sheet.cell_value(i, j) for j in range(sheet.ncols)]

        # Date (col 1) — Excel serial
        date_raw = row[1]
        if not date_raw or str(date_raw) in ["", "nan"]:
            continue
        date_str = _excel_serial_to_date(date_raw)
        if not date_str:
            continue

        particulars = _clean_description(str(row[3]))
        debit       = _parse_amount(row[5])
        credit      = _parse_amount(row[6])
        balance     = _parse_amount(row[7])
        part_tran   = str(row[16]).strip().upper() if len(row) > 16 else ""
        ref         = _clean_description(str(row[17])) if len(row) > 17 else ""

        txn_type = "CREDIT" if part_tran == "C" else ("DEBIT" if part_tran == "D" else
                   ("CREDIT" if credit > 0 else "DEBIT"))
        status   = _detect_status(particulars)

        transactions.append({
            "txn_id":        f"{account_no}_{i:04d}",
            "date":          date_str,
            "particulars":   particulars,
            "debit":         debit,
            "credit":        credit,
            "balance":       balance,
            "txn_type":      txn_type,
            "status":        status,
            "ref_number":    ref if ref else _extract_ref(particulars),
            "raw_row_index": i,
        })

    return {
        "account_number":  account_no,
        "bank_name":       "IndusInd Bank",
        "owner_name":      account_name,
        "branch":          None,
        "ifsc":            None,
        "email":           None,
        "period_from":     None,
        "period_to":       None,
        "opening_balance": None,
        "closing_balance": None,
        "source_file":     Path(file_path).name,
        "parse_method":    "xlsx_indusind",
        "transactions":    transactions,
        "parse_warnings":  warnings,
    }


# ── SBI XLS ───────────────────────────────────────────────────────────────────

def _parse_sbi_xls(file_path: str, df: pd.DataFrame) -> dict:
    """
    SBI format:
    Rows 0-19: metadata (account name, address, IFSC, etc.)
    Row 20: headers — Post Date | Value Date | Description | ChequeNo/Reference No |
                       Debit | Credit | Balance
    Rows 21+: data. Row 21 is 'Brought Forword' (skip it).
    Description has embedded \n\n — clean them.
    txn_type: if Debit col has value → DEBIT, elif Credit col has value → CREDIT
    Also check description prefix: DEP TFR = credit, WDL TFR = debit
    """
    meta = {}
    # Extract metadata from first 20 rows
    for i in range(min(20, len(df))):
        row_vals = [str(v).strip() for v in df.iloc[i].values if str(v) != 'nan']
        row_str  = ' '.join(row_vals).lower()
        if 'account_name' in row_str or 'account name' in row_str:
            # Value is in col 1 typically
            for j, v in enumerate(df.iloc[i].values):
                if str(v).strip() not in ['nan', ''] and j > 0:
                    meta['owner_name'] = str(v).strip()
                    break
        if 'account number' in row_str or 'account_number' in row_str:
            # Account Number label is in one cell, value is in the NEXT non-empty cell
            row_vals_all = list(df.iloc[i].values)
            for j, v in enumerate(row_vals_all):
                cell = str(v).strip()
                if cell.lower() in ['account number', 'account_number']:
                    # Value is in the next non-empty cell
                    for k in range(j+1, len(row_vals_all)):
                        nxt = str(row_vals_all[k]).strip()
                        if nxt not in ['nan', ''] and re.match(r'\d{8,}', nxt):
                            meta['account_number'] = nxt
                            break
                    break
        if 'ifsc' in row_str:
            for j, v in enumerate(df.iloc[i].values):
                if str(v).strip() not in ['nan', ''] and j > 2:
                    meta['ifsc'] = str(v).strip()
                    break
        if 'branch name' in row_str:
            for j, v in enumerate(df.iloc[i].values):
                if str(v).strip() not in ['nan', ''] and j > 2:
                    meta['branch'] = str(v).strip()
                    break

    account_no = meta.get('account_number', 'UNKNOWN')
    transactions = []
    warnings     = []

    # Data starts at row 22 (0-indexed), skip row 21 ('Brought Forword')
    for i in range(22, len(df)):
        row = df.iloc[i]
        vals = [str(v).strip() if str(v) != 'nan' else '' for v in row.values]

        date_str = _parse_date_str(vals[0]) if vals[0] else None
        if not date_str:
            continue

        particulars = _clean_description(vals[2])
        if not particulars or particulars.lower() in ['brought forward', 'brought forword', 'closing balance']:
            continue

        ref    = _clean_description(vals[3]) if len(vals) > 3 else ""
        debit  = _parse_amount(vals[4]) if len(vals) > 4 else 0.0
        credit = _parse_amount(vals[5]) if len(vals) > 5 else 0.0
        balance = _parse_amount(vals[6]) if len(vals) > 6 else 0.0

        # Determine txn_type from amounts first, then description prefix as fallback
        if debit > 0 and credit == 0:
            txn_type = "DEBIT"
        elif credit > 0 and debit == 0:
            txn_type = "CREDIT"
        else:
            p_lower = particulars.lower()
            if any(p_lower.startswith(pfx) for pfx in SBI_CREDIT_PREFIXES):
                txn_type = "CREDIT"
            elif any(p_lower.startswith(pfx) for pfx in SBI_DEBIT_PREFIXES):
                txn_type = "DEBIT"
            else:
                txn_type = "UNKNOWN"

        status = _detect_status(particulars)

        transactions.append({
            "txn_id":        f"{account_no}_{i:04d}",
            "date":          date_str,
            "particulars":   particulars,
            "debit":         debit,
            "credit":        credit,
            "balance":       balance,
            "txn_type":      txn_type,
            "status":        status,
            "ref_number":    ref if ref else _extract_ref(particulars),
            "raw_row_index": i,
        })

    return {
        "account_number":  account_no,
        "bank_name":       "State Bank of India",
        "owner_name":      meta.get('owner_name', 'UNKNOWN'),
        "branch":          meta.get('branch'),
        "ifsc":            meta.get('ifsc'),
        "email":           None,
        "period_from":     None,
        "period_to":       None,
        "opening_balance": None,
        "closing_balance": None,
        "source_file":     Path(file_path).name,
        "parse_method":    "xlsx_sbi",
        "transactions":    transactions,
        "parse_warnings":  warnings,
    }


# ── Generic CSV/XLSX ──────────────────────────────────────────────────────────

def _parse_generic(df: pd.DataFrame, source_file: str, parse_method: str) -> dict:
    """Fallback for any standard format with Date/Debit/Credit/Balance headers."""
    from app.parsers.pdf_parser import (
        _find_header_row, _extract_metadata_from_text,
        _parse_date, _parse_amount as _pa, _detect_status as _ds, _extract_ref_number
    )

    rows_as_str = [[str(c).strip() if str(c) != 'nan' else '' for c in row]
                   for row in df.values.tolist()]
    rows_as_str.insert(0, [str(c) for c in df.columns.tolist()])

    header_idx, col_map = _find_header_row(rows_as_str)
    if header_idx is None:
        raise ValueError("Could not find header row in spreadsheet.")

    meta_text = " ".join(" ".join(r) for r in rows_as_str[:header_idx])
    meta      = _extract_metadata_from_text(meta_text)
    acc       = meta.get("account_number", "UNKNOWN")

    transactions = []
    for row_idx, row in enumerate(rows_as_str[header_idx + 1:]):
        def gc(key, default=""):
            idx = col_map.get(key)
            return row[idx] if idx is not None and idx < len(row) else default

        date_raw    = gc("date")
        particulars = gc("particulars")
        debit       = _pa(gc("debit"))
        credit      = _pa(gc("credit"))
        balance     = _pa(gc("balance"))
        ref         = gc("ref")

        parsed_date = _parse_date(date_raw)
        if not parsed_date and balance == 0:
            continue
        if any(kw in particulars.lower() for kw in ["total", "opening balance", "closing balance", "brought forward"]):
            continue

        txn_type = "DEBIT" if debit > 0 and credit == 0 else ("CREDIT" if credit > 0 else "UNKNOWN")
        status   = _ds(particulars)

        transactions.append({
            "txn_id":        f"{acc}_{row_idx:04d}",
            "date":          parsed_date or date_raw,
            "particulars":   particulars,
            "debit":         debit,
            "credit":        credit,
            "balance":       balance,
            "txn_type":      txn_type,
            "status":        status,
            "ref_number":    ref or _extract_ref_number(particulars),
            "raw_row_index": row_idx,
        })

    return {**meta,
            "source_file":  source_file,
            "parse_method": parse_method,
            "transactions": transactions,
            "parse_warnings": []}


# ── Public entry points ───────────────────────────────────────────────────────

def _detect_xls_bank(file_path: str) -> str:
    """
    Peek at the XLS to decide which parser to use.
    Returns: 'indusind' | 'sbi' | 'generic'
    """
    try:
        import xlrd
        wb = xlrd.open_workbook(file_path)
        sheet = wb.sheets()[0]
        if sheet.nrows >= 3:
            row2 = [str(sheet.cell_value(2, j)).upper() for j in range(min(sheet.ncols, 5))]
            if "TRAN DATE" in row2 or "PART TRAN TYPE" in ' '.join(
                    [str(sheet.cell_value(2, j)) for j in range(sheet.ncols)]).upper():
                return 'indusind'
    except Exception:
        pass

    try:
        df = pd.read_excel(file_path, header=None, dtype=str, nrows=25)
        for i in range(len(df)):
            row_str = ' '.join([str(v) for v in df.iloc[i].values if str(v) != 'nan']).lower()
            if 'post date' in row_str and 'description' in row_str:
                return 'sbi'
    except Exception:
        pass

    return 'generic'


def parse_xls(file_path: str) -> dict:
    bank = _detect_xls_bank(file_path)
    logger.info(f"XLS bank detected: {bank} for {Path(file_path).name}")

    if bank == 'indusind':
        return _parse_indusind_xls(file_path)

    # For SBI and generic, load with pandas
    try:
        import xlrd
        df = pd.read_excel(file_path, header=None, dtype=str, engine='xlrd')
    except Exception:
        df = pd.read_excel(file_path, header=None, dtype=str, engine='openpyxl')

    if bank == 'sbi':
        return _parse_sbi_xls(file_path, df)

    return _parse_generic(df, Path(file_path).name, "xls_generic")


def parse_xlsx(file_path: str) -> dict:
    try:
        df = pd.read_excel(file_path, header=None, dtype=str, engine='openpyxl')
    except Exception as e:
        raise ValueError(f"Could not read XLSX: {e}")
    return _parse_generic(df, Path(file_path).name, "xlsx")


def parse_csv(file_path: str) -> dict:
    for enc in ["utf-8", "utf-8-sig", "latin-1", "ISO-8859-1"]:
        try:
            df = pd.read_csv(file_path, encoding=enc, header=None, dtype=str)
            return _parse_generic(df, Path(file_path).name, "csv")
        except Exception:
            continue
    raise ValueError("Could not read CSV with any common encoding.")
