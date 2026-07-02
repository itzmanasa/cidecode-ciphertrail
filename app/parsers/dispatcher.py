"""
dispatcher.py — Now uses ParserRegistry (Day 3 upgrade)
All format detection is handled by registry.py.
OCR is the final fallback for PDFs only.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".xls", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}


def _peek_pdf_text(file_path: str) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            return pdf.pages[0].extract_text() or "" if pdf.pages else ""
    except Exception:
        return ""


def dispatch_parse(file_path: str) -> dict:
    """
    Route file to correct parser via registry.
    PDF fallback: if registry parser returns 0 transactions → try OCR.
    """
    from app.parsers.registry import registry

    path = Path(file_path)
    ext  = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}")

    peek = _peek_pdf_text(file_path) if ext == ".pdf" else ""

    try:
        parser = registry.get_parser(file_path, peek_text=peek)
        result = parser.parse(file_path)

        # PDF-only OCR fallback
        if ext == ".pdf" and not result.get("transactions"):
            logger.warning(f"Parser {parser.__class__.__name__} returned 0 transactions — trying OCR")
            from app.parsers.ocr_parser import parse_pdf_ocr
            result = parse_pdf_ocr(file_path)

        return result

    except Exception as e:
        logger.error(f"dispatch_parse failed for {path.name}: {e}")
        # Last resort OCR for PDFs
        if ext == ".pdf":
            logger.info(f"Last-resort OCR for {path.name}")
            from app.parsers.ocr_parser import parse_pdf_ocr
            return parse_pdf_ocr(file_path)
        raise
