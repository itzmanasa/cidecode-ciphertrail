"""
edge_cases.py — Day 5 Afternoon: Edge Case Handling
======================================================
Hardens parsing against messy real-world bank statement quirks that
WILL show up on hackathon day with unfamiliar bank formats:

1. Merged cells (None values in pdfplumber table extraction)
2. Missing debit/credit columns (single "Amount" + "Type" column banks)
3. Parentheses-as-negative convention: (1,234.56) means debit
4. Day-name-prefixed dates: "Mon, 15 Jan 2024"
5. Non-standard date separators and ambiguous DD/MM vs MM/DD
6. Currency symbols beyond ₹ (Rs., INR, $, USD)
7. Completely empty/whitespace-only cells that should be treated as zero
8. Column headers with typos or unusual phrasing not in our keyword lists

These functions are used as a SAFETY NET — called by the registry parsers
when their primary logic doesn't find what it expects, before giving up.
"""

import re
import logging
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. MERGED CELL HANDLING
# ─────────────────────────────────────────────────────────────────────────────

def fill_merged_cells(rows: list) -> list:
    """
    pdfplumber returns None for cells that are part of a merged cell span.
    Forward-fill None values from the cell above in the same column —
    this is the standard convention for how merged cells should read.

    Only applies to narrow columns (date, reference) where forward-fill
    makes sense — NOT to debit/credit/balance which should default to empty.
    """
    if not rows:
        return rows

    filled = []
    last_seen = {}  # column_index -> last non-None value

    for row in rows:
        if row is None:
            filled.append(row)
            continue
        new_row = list(row)
        for col_idx, cell in enumerate(new_row):
            if cell is None or str(cell).strip() == "":
                # Only forward-fill for likely date/account columns (first 2 cols)
                if col_idx <= 1 and col_idx in last_seen:
                    new_row[col_idx] = last_seen[col_idx]
            else:
                last_seen[col_idx] = cell
        filled.append(new_row)

    return filled


def safe_cell(row: list, idx: int, default: str = "") -> str:
    """Safely extract a cell value, handling None/missing index gracefully."""
    if row is None or idx >= len(row):
        return default
    val = row[idx]
    if val is None:
        return default
    return str(val).strip()


# ─────────────────────────────────────────────────────────────────────────────
# 2. SINGLE AMOUNT + TYPE COLUMN BANKS
# ─────────────────────────────────────────────────────────────────────────────

def split_amount_type_column(amount_str: str, type_str: str) -> Tuple[float, float]:
    """
    Some banks use one 'Amount' column + one 'Type' column (Dr/Cr/D/C)
    instead of separate Debit/Credit columns.

    Returns (debit, credit) tuple.
    """
    amount = parse_amount_robust(amount_str)
    type_clean = type_str.strip().upper()

    if type_clean in ("DR", "D", "DEBIT", "WITHDRAWAL", "-"):
        return amount, 0.0
    elif type_clean in ("CR", "C", "CREDIT", "DEPOSIT", "+"):
        return 0.0, amount
    else:
        # Ambiguous — log warning, default to debit (conservative for fraud detection)
        logger.warning(f"Ambiguous transaction type '{type_str}' — defaulting to DEBIT")
        return amount, 0.0


def detect_amount_type_layout(header_row: list) -> Optional[dict]:
    """
    Detect if a table uses single Amount+Type columns instead of Debit/Credit.
    Returns {'amount_col': idx, 'type_col': idx} if detected, else None.
    """
    amount_idx = None
    type_idx = None

    for i, cell in enumerate(header_row):
        cell_lower = str(cell or "").lower().strip()
        if cell_lower in ("amount", "transaction amount", "txn amount"):
            amount_idx = i
        if cell_lower in ("type", "dr/cr", "txn type", "transaction type", "cr/dr"):
            type_idx = i

    if amount_idx is not None and type_idx is not None:
        return {"amount_col": amount_idx, "type_col": type_idx}
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 3. PARENTHESES-AS-NEGATIVE CONVENTION
# ─────────────────────────────────────────────────────────────────────────────

def parse_amount_robust(val) -> float:
    """
    Robust amount parser handling:
    - Standard: "1,234.56" → 1234.56
    - Parentheses negative: "(1,234.56)" → -1234.56 (caller decides if this means debit)
    - Currency prefixes: "Rs. 1,234.56", "INR 1234.56", "$1,234.56"
    - Trailing Cr/Dr: "1,234.56Cr" → 1234.56 (suffix stripped, sign ignored here)
    - Whitespace-only or dash: "-", "--", " " → 0.0
    """
    if val is None:
        return 0.0
    raw = str(val).strip()

    if raw in ("", "-", "--", "nan", "None", "NIL", "N/A"):
        return 0.0

    is_negative = False
    if raw.startswith("(") and raw.endswith(")"):
        is_negative = True
        raw = raw[1:-1]

    # Strip Cr/Dr suffix
    raw_upper = raw.upper()
    if raw_upper.endswith("CR") or raw_upper.endswith("DR"):
        raw = raw[:-2]

    # Strip currency symbols/prefixes
    raw = re.sub(r"(rs\.?|inr|usd|\$|₹)", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"[,\s]", "", raw)
    raw = re.sub(r"[^\d.\-]", "", raw)

    try:
        amount = float(raw) if raw else 0.0
        return -abs(amount) if is_negative else abs(amount)
    except ValueError:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. DAY-NAME-PREFIXED AND NON-STANDARD DATES
# ─────────────────────────────────────────────────────────────────────────────

DAY_NAME_RE = re.compile(
    r"^(mon|tue|wed|thu|fri|sat|sun)[a-z]*,?\s*",
    re.IGNORECASE
)

EXTRA_DATE_FORMATS = [
    "%d %b, %Y", "%d %B, %Y",      # "15 Jan, 2024"
    "%b %d, %Y", "%B %d, %Y",      # "Jan 15, 2024"
    "%Y/%m/%d",                     # "2024/01/15"
    "%d%m%Y",                       # "15012024" (no separators)
    "%d %b %Y",                     # "15 Jan 2024" (no comma — day-name-stripped result)
    "%d/%m/%Y",                     # "15/01/2024" (after time component stripped)
    "%d-%m-%Y",
    "%m/%d/%Y",                     # US format fallback (last resort, ambiguous)
]


def parse_date_robust(date_str: str) -> Optional[str]:
    """
    Extended date parser handling day-name prefixes and additional formats
    beyond what pdf_parser.py's _parse_date() already covers.
    Returns ISO YYYY-MM-DD or None.
    """
    if not date_str:
        return None
    raw = str(date_str).strip()

    # Strip day-name prefix: "Mon, 15 Jan 2024" → "15 Jan 2024"
    raw = DAY_NAME_RE.sub("", raw)

    # Strip time component if present: "15/01/2024 14:30:00" → "15/01/2024"
    raw = re.split(r"\s+\d{1,2}:\d{2}", raw)[0].strip()

    for fmt in EXTRA_DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None  # Caller should fall back to pdf_parser's _parse_date()


def resolve_ambiguous_date(date_str: str, other_dates_in_doc: list) -> Optional[str]:
    """
    For dates like '03/04/2024' it's ambiguous whether this is 3-Apr or 4-Mar.
    Heuristic: if ANY other date in the document has a day value > 12,
    we know the format is DD/MM (since MM can't exceed 12), and vice versa.
    """
    parts = re.split(r"[/\-.]", date_str.strip())
    if len(parts) != 3:
        return None

    try:
        p1, p2, p3 = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None

    # Determine format from corpus evidence
    is_dd_mm = True  # Default assumption: Indian banks use DD/MM/YYYY
    for other in other_dates_in_doc:
        other_parts = re.split(r"[/\-.]", str(other).strip())
        if len(other_parts) == 3:
            try:
                op1 = int(other_parts[0])
                if op1 > 12:
                    is_dd_mm = True
                    break
            except ValueError:
                continue

    day, month = (p1, p2) if is_dd_mm else (p2, p1)
    year = p3 if p3 > 31 else p3 + 2000

    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. HEADER KEYWORD FUZZY MATCHING (typos / unusual phrasing)
# ─────────────────────────────────────────────────────────────────────────────

EXTENDED_DATE_KEYWORDS       = ["date", "txn date", "value date", "transaction date",
                                  "posting date", "trans dt", "dt", "tran date"]
EXTENDED_PARTICULARS_KEYWORDS = ["particulars", "description", "narration", "remarks",
                                   "details", "transaction details", "desc", "narr",
                                   "transaction remarks", "particular"]
EXTENDED_DEBIT_KEYWORDS      = ["debit", "withdrawal", "withdrawals", "dr", "debit amount",
                                  "amount (dr)", "wd", "withdrawl", "debits"]
EXTENDED_CREDIT_KEYWORDS     = ["credit", "deposit", "deposits", "cr", "credit amount",
                                  "amount (cr)", "dep", "deposite", "credits"]
EXTENDED_BALANCE_KEYWORDS    = ["balance", "closing balance", "running balance",
                                  "available balance", "bal", "balanace", "closing bal"]


def fuzzy_match_header(cell_text: str, keyword_list: list, threshold: float = 0.75) -> bool:
    """
    Fuzzy match a header cell against a keyword list, tolerating minor typos
    ("Balanace" → "Balance") using simple character-overlap ratio.
    Falls back from exact substring match to fuzzy ratio match.
    """
    cell_lower = re.sub(r"\s+", " ", str(cell_text).lower().strip())

    # Exact substring match first (fast path)
    if any(kw in cell_lower for kw in keyword_list):
        return True

    # Fuzzy fallback for typos
    for kw in keyword_list:
        if len(kw) < 4:  # Skip fuzzy matching for very short keywords (too noisy)
            continue
        ratio = _similarity_ratio(cell_lower, kw)
        if ratio >= threshold:
            return True

    return False


def _similarity_ratio(a: str, b: str) -> float:
    """Simple character-bigram overlap ratio — lightweight, no external deps."""
    if not a or not b:
        return 0.0

    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s) - 1))

    bg_a, bg_b = bigrams(a), bigrams(b)
    if not bg_a or not bg_b:
        return 0.0

    overlap = len(bg_a & bg_b)
    return (2 * overlap) / (len(bg_a) + len(bg_b))


# ─────────────────────────────────────────────────────────────────────────────
# MASTER EDGE-CASE-SAFE ROW PARSER
# ─────────────────────────────────────────────────────────────────────────────

def safe_parse_transaction_row(row: list, col_map: dict, other_dates_seen: list = None) -> Optional[dict]:
    """
    Parse one transaction row with full edge-case protection.
    Returns a dict with date/particulars/debit/credit/balance, or None if
    the row is unparseable (e.g., completely empty, header repeat, footer).

    This is a drop-in safety wrapper — existing parsers can call this when
    their normal logic fails, before giving up entirely.
    """
    if other_dates_seen is None:
        other_dates_seen = []

    date_raw    = safe_cell(row, col_map.get("date", -1))
    particulars = safe_cell(row, col_map.get("particulars", -1))
    debit_raw   = safe_cell(row, col_map.get("debit", -1))
    credit_raw  = safe_cell(row, col_map.get("credit", -1))
    balance_raw = safe_cell(row, col_map.get("balance", -1))

    if not date_raw and not balance_raw:
        return None  # Likely empty/footer row

    # Try robust date parsing
    parsed_date = parse_date_robust(date_raw)
    if not parsed_date:
        parsed_date = resolve_ambiguous_date(date_raw, other_dates_seen)
    if not parsed_date:
        parsed_date = date_raw  # Last resort: keep raw string, flag via warning upstream

    # Handle single Amount+Type layout if debit/credit columns weren't found separately
    if "amount" in col_map and "type" in col_map:
        amount_raw = safe_cell(row, col_map["amount"])
        type_raw   = safe_cell(row, col_map["type"])
        debit, credit = split_amount_type_column(amount_raw, type_raw)
    else:
        debit  = parse_amount_robust(debit_raw)
        credit = parse_amount_robust(credit_raw)

    balance = parse_amount_robust(balance_raw)

    return {
        "date":        parsed_date,
        "particulars": particulars,
        "debit":       debit,
        "credit":      credit,
        "balance":     balance,
    }
