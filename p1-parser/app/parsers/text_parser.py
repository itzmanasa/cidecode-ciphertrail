"""
text_parser.py — Multi-bank fixed-width plain-text statement parser

Supported formats:
  1. Kerala Gramin Bank (KLGB) — dd-mm-yy date, space-separated Cr/Dr suffix
  2. Punjab National Bank (PNB) — dd-mm-yyyy date, balanceCr/Dr with no space

Auto-detects format from header content.
"""

import re
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

FAILED_MARKERS   = ["failed", "failure", "reversed", "reversal", "returned",
                    "bounce", "bounced", "neft ret", "neft return", "rtn",
                    "reject", "rejected", "insuffbal", "insuff bal",
                    "insufficient", "inward return"]
REVERSAL_MARKERS = ["reversal", "reversed", "rev-", "rev ", "return",
                    "returned", "ft-rev"]

# ─────────────────────────────────────────────
# SHARED UTILITIES
# ─────────────────────────────────────────────

def _parse_amount(val: str) -> float:
    if not val or val.strip() in ("", "-", "--", "nan"):
        return 0.0
    raw = re.sub(r"[₹$\s]", "", val.strip())
    raw = re.sub(r"[^\d.\-]", "", raw.replace(",", ""))
    try:
        return abs(float(raw))
    except ValueError:
        return 0.0

def _parse_date(date_str: str) -> str:
    raw = date_str.strip()
    for fmt in ["%d-%m-%y", "%d-%m-%Y", "%d/%m/%Y", "%d/%m/%y",
                "%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(raw[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw

def _detect_mode(particulars: str) -> str:
    p = particulars.upper()
    if p.startswith("UPI"):
        return "UPI"
    if "CWDR" in p or "ATM WDR" in p or "ATM WDR" in p or "ATM/" in p:
        return "CASH_WITHDRAWAL"
    if "NEFT" in p:
        return "NEFT"
    if "IMPS" in p:
        return "IMPS"
    if "RTGS" in p:
        return "RTGS"
    if "CHQ" in p or "CHEQUE" in p or "CLG" in p or "CMS" in p:
        return "CHEQUE"
    if "BY CASH" in p or "CASH DEP" in p or "CASH CR" in p:
        return "CASH_DEPOSIT"
    if "CBDCL" in p:
        return "CBDC"
    if "P2M" in p or "P2V" in p:
        return "UPI"
    return "OTHER"

def _get_status(particulars: str) -> str:
    p = particulars.lower()
    if any(m in p for m in FAILED_MARKERS):
        return "FAILED"
    if any(m in p for m in REVERSAL_MARKERS):
        return "REVERSAL"
    return "SUCCESS"

def _make_txn(counter, date, particulars, debit, credit, balance, bal_sign="Cr") -> dict:
    if bal_sign.upper() == "Dr":
        balance = -balance
    status = _get_status(particulars)
    upi_m  = re.search(r"UPI/(\d+)", particulars, re.IGNORECASE)
    return {
        "txn_id":      f"TXT_{counter:05d}",
        "date":        date,
        "value_date":  date,
        "particulars": particulars,
        "debit":       debit,
        "credit":      credit,
        "balance":     balance,
        "txn_type":    "CREDIT" if (credit > 0 and debit == 0) else
                       "DEBIT"  if (debit  > 0 and credit == 0) else "UNKNOWN",
        "status":      status,
        "is_reversal": status in ("FAILED", "REVERSAL"),
        "ref_number":  upi_m.group(1) if upi_m else None,
        "mode":        _detect_mode(particulars),
    }

# ─────────────────────────────────────────────
# FORMAT 1: KERALA GRAMIN BANK
# ─────────────────────────────────────────────
# Header: "Trans Dt Value Dt Transn ID ... Debit Credit Balance"
# Date format: dd-mm-yy (2-digit year)
# Balance: "500.00 Cr" (space before sign)

_KLGB_AMT = re.compile(
    r'(?:([\d,]+\.\d{2})\s+)?'
    r'(?:([\d,]+\.\d{2})\s+)?'
    r'([\d,]+\.\d{2})\s+(Cr|Dr)\s*$',
    re.IGNORECASE
)

def _klgb_get_zones(header_line: str) -> dict:
    def pos(label):
        idx = header_line.find(label)
        return idx if idx != -1 else None
    return {
        "particulars": pos("Transaction Particulars"),
        "ins_number":  pos("Ins Number"),
        "debit":       pos("Debit"),
        "credit":      pos("Credit"),
        "balance":     pos("Balance"),
    }

def _klgb_parse_amounts(line: str, zones: dict):
    d_col = zones["debit"]
    c_col = zones["credit"]
    right = line[82:] if len(line) > 82 else line
    m = _KLGB_AMT.search(right)
    if not m:
        return 0.0, 0.0, 0.0, "Cr"
    g1, g2, g3, sign = m.group(1), m.group(2), m.group(3), m.group(4)
    def f(s): return float(s.replace(",","")) if s else 0.0
    bal = f(g3)
    if g1 and g2:
        return f(g1), f(g2), bal, sign
    if g1 and not g2:
        debit_zone = line[d_col:c_col].strip() if (d_col and c_col and len(line) > c_col) else ""
        if debit_zone:
            return f(g1), 0.0, bal, sign
        return 0.0, f(g1), bal, sign
    return 0.0, 0.0, bal, sign

def _klgb_parse_line(line: str, zones: dict, counter: int):
    if not re.match(r"^\d{2}-\d{2}-\d{2}\s", line.strip()):
        return None
    if line.strip().startswith("-") or line.strip().lower().startswith("total"):
        return None
    raw_date    = line[0:8].strip()
    p_start     = zones["particulars"]
    p_end       = zones["ins_number"]
    particulars = re.sub(r"\s+", " ",
                  line[p_start:p_end].strip()) if (p_start and p_end) else ""
    debit, credit, balance, sign = _klgb_parse_amounts(line, zones)
    return _make_txn(counter, _parse_date(raw_date), particulars,
                     debit, credit, balance, sign)

def _parse_klgb(lines: list) -> tuple:
    """Returns (header_dict, transactions_list)"""
    header = {
        "bank_name": None, "account_number": None, "owner_name": None,
        "branch": None, "period_from": None, "period_to": None,
    }
    for line in lines[:30]:
        s = line.strip()
        if not header["bank_name"] and s and not s.startswith("-"):
            header["bank_name"] = s
        acc = re.search(r"Account\s+Number\s*:\s*([A-Z0-9]+\s+[\d]+)\s+(.+)",
                        line, re.IGNORECASE)
        if acc:
            header["account_number"] = acc.group(1).strip().replace(" ","")
            header["owner_name"]     = acc.group(2).strip()
        f = re.search(r"From\s+Date\s*:\s*(\S+)", line, re.IGNORECASE)
        if f: header["period_from"] = _parse_date(f.group(1))
        t = re.search(r"To\s+Date\s*:\s*(\S+)", line, re.IGNORECASE)
        if t: header["period_to"]   = _parse_date(t.group(1))
        b = re.search(r"([A-Z ]+)\s*\((\d{5})\)", s)
        if b and not header["branch"]: header["branch"] = b.group(0).strip()

    hdr_idx = next((i for i, l in enumerate(lines)
                    if "Trans Dt" in l and "Debit" in l), -1)
    if hdr_idx == -1:
        raise ValueError("KLGB header not found")
    zones = _klgb_get_zones(lines[hdr_idx])

    txns, n = [], 1
    for line in lines[hdr_idx + 2:]:
        if not line.strip() or line.strip().startswith("---"): continue
        if "CERTIFICATE" in line or "Certified that" in line: break
        t = _klgb_parse_line(line, zones, n)
        if t:
            txns.append(t)
            n += 1
    return header, txns

# ─────────────────────────────────────────────
# FORMAT 2: PUNJAB NATIONAL BANK
# ─────────────────────────────────────────────
# Header: "GL. Date  Value Date  Instrmnt Number  Particulars  Debit Amount  Credit Amount  Balance  Entry User"
# Date format: dd-mm-yyyy (4-digit year), leading space on each line
# Balance: "1,40,231.00Cr" (NO space before sign), then user id

_PNB_AMT = re.compile(
    r'(?:([\d,]+\.\d{2})\s+)?'
    r'(?:([\d,]+\.\d{2})\s+)?'
    r'([\d,]+\.\d{2})(Cr|Dr)\s',
    re.IGNORECASE
)

def _pnb_parse_line(line: str, counter: int):
    """Parse one PNB transaction line."""
    stripped = line.strip()
    # Must start with dd-mm-yyyy
    if not re.match(r"^\d{2}-\d{2}-\d{4}", stripped):
        return None
    if stripped.startswith("-") or stripped.lower().startswith("b/f"):
        return None

    # Dates at fixed positions (with leading space stripped)
    raw_date = stripped[0:10]

    # Particulars: from col 40 (relative to stripped) to the numeric zone
    # The numeric zone starts around col 88 in stripped line
    # Find first digit cluster that looks like an amount
    particulars_raw = stripped[37:88].strip()
    particulars = re.sub(r"\s+", " ", particulars_raw)

    # Extract amounts from right side (col 88 onward)
    right = stripped[88:] if len(stripped) > 88 else stripped
    m = _PNB_AMT.search(right)
    if not m:
        # Try with full line right side
        right = line[90:] if len(line) > 90 else line
        m = _PNB_AMT.search(right)
    if not m:
        return None

    g1, g2, bal_s, sign = m.group(1), m.group(2), m.group(3), m.group(4)
    def f(s): return float(s.replace(",","")) if s else 0.0
    balance = f(bal_s)

    if g1 and g2:
        debit, credit = f(g1), f(g2)
    elif g1 and not g2:
        # Disambiguate: check debit zone (col 90-128 of original line) vs credit zone (128-148)
        debit_zone  = line[90:128].strip() if len(line) > 128 else ""
        has_d = bool(re.search(r"[\d,]+\.\d{2}", debit_zone))
        if has_d:
            debit, credit = f(g1), 0.0
        else:
            debit, credit = 0.0, f(g1)
    else:
        debit, credit = 0.0, 0.0

    return _make_txn(counter, _parse_date(raw_date), particulars,
                     debit, credit, balance, sign)

def _parse_pnb(lines: list) -> tuple:
    header = {
        "bank_name": "Punjab National Bank",
        "account_number": None, "owner_name": None,
        "branch": None, "period_from": None, "period_to": None,
    }
    for line in lines:
        # Account No: 3127637522775626  INR SHIV LAL BISHNOI
        acc = re.search(r"Account\s+No\s*:\s*([\d]+)\s+\w+\s+(.+)", line, re.IGNORECASE)
        if acc:
            header["account_number"] = acc.group(1).strip()
            header["owner_name"]     = acc.group(2).strip()
        # Service OutLet / branch
        sol = re.search(r"Service\s+OutLet\s*:\s*\d+\s+(.+)", line, re.IGNORECASE)
        if sol and not header["branch"]: header["branch"] = sol.group(1).strip()
        # Period from the report header
        per = re.search(r"from\s+(\d{2}-\d{2}-\d{4})\s+to\s+(\d{2}-\d{2}-\d{4})", line, re.IGNORECASE)
        if per:
            header["period_from"] = _parse_date(per.group(1))
            header["period_to"]   = _parse_date(per.group(2))
        # Bank name from top line
        bnk = re.search(r"PUNJAB NATIONAL BANK[,\s]+(\w+)", line, re.IGNORECASE)
        if bnk and not header["bank_name"]:
            header["bank_name"] = "Punjab National Bank"

    txns, n = [], 1
    in_data = False
    for line in lines:
        if "---" in line and "Debit Amount" not in line:
            in_data = True
            continue
        if not in_data:
            continue
        if "Page Total" in line or "Closing Balance" in line or \
           "Total Credit" in line or "Signature" in line:
            continue
        # Skip page break header lines
        if "Customer Account Ledger" in line or "GL." in line or \
           "Service OutLet" in line or "Account No" in line or \
           "Opening Balance" in line or "B/F Balance" in line or \
           "Peg Review" in line:
            continue
        t = _pnb_parse_line(line, n)
        if t:
            txns.append(t)
            n += 1
    return header, txns

# ─────────────────────────────────────────────
# FORMAT DETECTION
# ─────────────────────────────────────────────

def _detect_format(lines: list) -> str:
    """Return 'klgb', 'pnb', or 'unknown'."""
    text = "\n".join(lines[:80]).upper()
    if "KERALA GRAMIN BANK" in text or "TRANS DT" in text:
        return "klgb"
    if "PUNJAB NATIONAL BANK" in text or "GL. DATE" in text or \
       "CUSTOMER ACCOUNT LEDGER" in text:
        return "pnb"
    # Fallback: try to detect by line date format
    for line in lines[:100]:
        if re.match(r"^\s*\d{2}-\d{2}-\d{4}\s+\d{2}-\d{2}-\d{4}", line.strip()):
            return "pnb"
        if re.match(r"^\d{2}-\d{2}-\d{2}\s", line.strip()):
            return "klgb"
    return "unknown"

# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def parse_text_statement(file_path: str) -> dict:
    path = Path(file_path)
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = [l.rstrip("\n").rstrip("\r") for l in f.readlines()]

    fmt = _detect_format(lines)
    logger.info(f"text_parser: detected format '{fmt}' for {path.name}")

    if fmt == "klgb":
        header, transactions = _parse_klgb(lines)
    elif fmt == "pnb":
        header, transactions = _parse_pnb(lines)
    else:
        raise ValueError(f"Unrecognised .txt bank statement format in {path.name}. "
                         f"Supported: Kerala Gramin Bank, Punjab National Bank.")

    total_debit    = sum(t["debit"]  for t in transactions)
    total_credit   = sum(t["credit"] for t in transactions)
    reversal_count = sum(1 for t in transactions if t["is_reversal"])
    cash_wd        = [t for t in transactions if t["mode"] == "CASH_WITHDRAWAL"]

    logger.info(f"text_parser: {len(transactions)} txns | "
                f"{reversal_count} reversals | {len(cash_wd)} cash WDs | fmt={fmt}")

    return {
        "bank_name":       header.get("bank_name") or "Unknown Bank",
        "account_number":  header.get("account_number") or "UNKNOWN",
        "owner_name":      header.get("owner_name") or "Unknown",
        "branch":          header.get("branch"),
        "ifsc":            header.get("ifsc"),
        "email":           header.get("email"),
        "period_from":     header.get("period_from"),
        "period_to":       header.get("period_to"),
        "opening_balance": transactions[0]["balance"]  if transactions else None,
        "closing_balance": transactions[-1]["balance"] if transactions else None,
        "source_file":     path.name,
        "parse_method":    f"text_fixed_width_{fmt}",
        "transactions":    transactions,
        "parse_warnings":  [],
        "_summary": {
            "total_transactions":    len(transactions),
            "total_debit":           total_debit,
            "total_credit":          total_credit,
            "reversal_count":        reversal_count,
            "cash_withdrawal_count": len(cash_wd),
            "cash_withdrawal_total": sum(t["debit"] for t in cash_wd),
        }
    }
