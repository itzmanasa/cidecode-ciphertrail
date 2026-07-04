"""
ocr_parser.py — UPGRADED OCR Parser (Day 2)
Adds deskew + denoise preprocessing on top of Day 1's basic grayscale.

Preprocessing pipeline per image:
  1. Grayscale
  2. Denoise (median blur via PIL)
  3. Deskew (detect rotation angle, rotate back)
  4. Binarize (Otsu threshold via PIL)
  5. Upscale if image is small (below 1800px wide)

Then runs pytesseract with --psm 6 (uniform block).
Falls back to --psm 4 (single column) if row count is very low.
"""

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from PIL import Image, ImageFilter, ImageOps
from pdf2image import convert_from_path
import re
import logging
import math
import numpy as np
from pathlib import Path
from typing import List, Tuple

from app.parsers.pdf_parser import (
    _parse_date, _parse_amount, _detect_status,
    _extract_ref_number, _extract_metadata_from_text,
    _find_header_row,
)

logger = logging.getLogger(__name__)

TESS_CONFIG_BLOCK  = "--psm 6 --oem 3"
TESS_CONFIG_COLUMN = "--psm 4 --oem 3"
MIN_WIDTH_PX = 1800   # upscale images narrower than this


# ─────────────────────────────────────────────────────────────
# IMAGE PREPROCESSING
# ─────────────────────────────────────────────────────────────

def _to_grayscale(img: Image.Image) -> Image.Image:
    return img.convert("L")


def _denoise(img: Image.Image) -> Image.Image:
    """Median filter removes salt-and-pepper noise from scans."""
    return img.filter(ImageFilter.MedianFilter(size=3))


def _binarize(img: Image.Image) -> Image.Image:
    """
    Otsu-style binarization: convert to pure black/white.
    PIL doesn't have Otsu natively, so we use a fixed threshold of 150
    which works well for most bank statement scans.
    """
    return img.point(lambda p: 255 if p > 150 else 0, "1").convert("L")


def _deskew(img: Image.Image) -> Image.Image:
    """
    Detect and correct skew using projection profile method.
    Tries angles from -10 to +10 degrees, picks the one with
    maximum variance in horizontal projection (sharpest lines = correct angle).
    Fast enough for hackathon use (<1 sec per page at 300 DPI).
    """
    try:
        arr = np.array(img)
        best_angle = 0.0
        best_score = -1.0

        for angle in np.arange(-10, 10.5, 0.5):
            rotated = img.rotate(angle, expand=False, fillcolor=255)
            rot_arr = np.array(rotated)
            # Horizontal projection: sum pixels per row
            projection = np.sum(rot_arr < 128, axis=1).astype(float)
            score = float(np.var(projection))
            if score > best_score:
                best_score = score
                best_angle = angle

        if abs(best_angle) > 0.3:
            logger.info(f"Deskewing by {best_angle:.1f} degrees")
            return img.rotate(best_angle, expand=True, fillcolor=255)
        return img
    except Exception as e:
        logger.warning(f"Deskew failed (non-critical): {e}")
        return img


def _upscale_if_needed(img: Image.Image) -> Image.Image:
    """Upscale small images — Tesseract accuracy drops below ~150 DPI effective."""
    w, h = img.size
    if w < MIN_WIDTH_PX:
        scale = MIN_WIDTH_PX / w
        new_size = (int(w * scale), int(h * scale))
        logger.info(f"Upscaling image from {w}x{h} to {new_size[0]}x{new_size[1]}")
        return img.resize(new_size, Image.LANCZOS)
    return img


def preprocess_image(img: Image.Image) -> Image.Image:
    """
    Full preprocessing pipeline.
    Order matters: grayscale → upscale → denoise → deskew → binarize
    """
    img = _to_grayscale(img)
    img = _upscale_if_needed(img)
    img = _denoise(img)
    img = _deskew(img)
    img = _binarize(img)
    return img


# ─────────────────────────────────────────────────────────────
# OCR EXTRACTION
# ─────────────────────────────────────────────────────────────

def _image_to_rows(img: Image.Image) -> Tuple[List[List[str]], str]:
    """
    Preprocess image then run OCR.
    Tries --psm 6 first. If it gets < 5 rows, retries with --psm 4.
    Returns (rows, full_raw_text).
    """
    processed = preprocess_image(img)

    raw_text = pytesseract.image_to_string(processed, config=TESS_CONFIG_BLOCK)
    rows = _text_to_rows(raw_text)

    if len(rows) < 5:
        logger.warning("PSM 6 got < 5 rows, retrying with PSM 4 (single column mode)")
        raw_text = pytesseract.image_to_string(processed, config=TESS_CONFIG_COLUMN)
        rows = _text_to_rows(raw_text)

    return rows, raw_text


def _text_to_rows(raw_text: str) -> List[List[str]]:
    """Split OCR output into rows and columns."""
    rows = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        cols = re.split(r"\s{2,}", line)
        rows.append([c.strip() for c in cols if c.strip()])
    return rows


# ─────────────────────────────────────────────────────────────
# PUBLIC PARSE FUNCTIONS
# ─────────────────────────────────────────────────────────────

def parse_pdf_ocr(file_path: str) -> dict:
    """Parse a scanned PDF. Each page → image → preprocess → OCR."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info(f"OCR parse starting: {path.name} (30–90s expected)")
    images = convert_from_path(str(path), dpi=300)

    all_rows = []
    full_text = ""

    for page_num, img in enumerate(images):
        rows, page_text = _image_to_rows(img)
        all_rows.extend(rows)
        if page_num == 0:
            full_text = page_text
        logger.info(f"  Page {page_num + 1}/{len(images)}: {len(rows)} rows extracted")

    return _build_statement_from_rows(all_rows, full_text, path.name, "pdf_ocr")


def parse_image_ocr(file_path: str) -> dict:
    """Parse a single image file (JPG/PNG/TIFF)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    img = Image.open(str(path))
    all_rows, full_text = _image_to_rows(img)
    return _build_statement_from_rows(all_rows, full_text, path.name, "image_ocr")


# ─────────────────────────────────────────────────────────────
# SHARED BUILD LOGIC
# ─────────────────────────────────────────────────────────────

def _build_statement_from_rows(all_rows, full_text, source_filename, parse_method) -> dict:
    warnings = []
    transactions = []

    header_idx, col_map = _find_header_row(all_rows)
    if header_idx is None:
        raise ValueError(
            "OCR could not detect transaction header row. "
            "Image quality may be too low or bank format is unsupported."
        )

    meta = _extract_metadata_from_text(full_text)
    data_rows = all_rows[header_idx + 1:]
    row_index = 0

    for row in data_rows:
        if not row or not any(row):
            continue

        # Pad row to avoid index errors
        max_idx = max(col_map.values(), default=0)
        while len(row) <= max_idx:
            row.append("")

        def get_col(key, default=""):
            idx = col_map.get(key)
            if idx is not None and idx < len(row):
                return str(row[idx]).strip()
            return default

        date_raw    = get_col("date")
        particulars = get_col("particulars")
        debit_raw   = get_col("debit")
        credit_raw  = get_col("credit")
        balance_raw = get_col("balance")
        ref_raw     = get_col("ref")

        parsed_date = _parse_date(date_raw)
        if not parsed_date and not balance_raw:
            if transactions:
                transactions[-1]["particulars"] += " " + particulars
            continue

        debit   = _parse_amount(debit_raw)
        credit  = _parse_amount(credit_raw)
        balance = _parse_amount(balance_raw)

        if debit > 0 and credit == 0:
            txn_type = "DEBIT"
        elif credit > 0 and debit == 0:
            txn_type = "CREDIT"
        else:
            txn_type = "UNKNOWN"

        status     = _detect_status(particulars)
        ref_number = ref_raw if ref_raw else _extract_ref_number(particulars)
        txn_id     = f"{meta['account_number']}_{row_index:04d}"

        transactions.append({
            "txn_id":        txn_id,
            "date":          parsed_date or date_raw,
            "particulars":   particulars,
            "debit":         debit,
            "credit":        credit,
            "balance":       balance,
            "txn_type":      txn_type,
            "status":        status,
            "ref_number":    ref_number,
            "raw_row_index": row_index,
        })
        row_index += 1

    logger.info(f"OCR parse complete: {len(transactions)} transactions, {len(warnings)} warnings")

    return {
        "account_number":  meta["account_number"],
        "bank_name":       meta["bank_name"],
        "owner_name":      meta["owner_name"],
        "branch":          meta.get("branch"),
        "ifsc":            meta.get("ifsc"),
        "email":           meta.get("email"),
        "period_from":     meta.get("period_from"),
        "period_to":       meta.get("period_to"),
        "opening_balance": meta.get("opening_balance"),
        "closing_balance": meta.get("closing_balance"),
        "source_file":     source_filename,
        "parse_method":    parse_method,
        "transactions":    transactions,
        "parse_warnings":  warnings,
    }
