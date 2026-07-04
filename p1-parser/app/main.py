"""
main.py — FastAPI Application (Day 7 FINAL: offline cache + full pipeline)
"""
import sys
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path so offline_cache.py is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.routes.upload        import router as upload_router
from app.routes.multi_upload  import router as multi_upload_router
from app.routes.analyse       import router as analyse_router
from app.routes.transactions  import router as transactions_router
from app.routes.accounts      import router as accounts_router
from app.routes.cache_routes  import router as cache_router
from app.db.database          import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Forensic Bank Audit API",
    description=(
        "CideCode — Forensic Bank Statement Analyser.\n"
        "Multi-bank parser + FIFO/pre-credit audit + reversal detection + SQLite + offline cache."
    ),
    version="HACKATHON-FINAL",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router,       prefix="/api", tags=["1. Parser"])
app.include_router(multi_upload_router, prefix="/api", tags=["1. Parser"])
app.include_router(analyse_router,      prefix="/api", tags=["2. Reversal Detection"])
app.include_router(transactions_router, prefix="/api", tags=["3. Audit & Transactions"])
app.include_router(accounts_router,     prefix="/api", tags=["4. Database"])
app.include_router(cache_router,        prefix="/api", tags=["5. Offline Cache"])


@app.on_event("startup")
def startup():
    init_db()
    # Regenerate cache on every startup so it's always fresh
    try:
        from offline_cache import build_full_cache
        build_full_cache()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Cache build skipped: {e}")


@app.get("/health")
def health():
    from offline_cache import cache_exists
    return {
        "status": "ok",
        "version": "HACKATHON-FINAL",
        "offline_mode_ready": cache_exists("accounts") and cache_exists("all_transactions"),
    }


@app.get("/")
def root():
    return {
        "message": "CideCode Forensic Audit API — HACKATHON READY",
        "docs": "/docs",
        "team": "P1 (Parser) + P2 (Graph) + P3 (Frontend)",
        "quick_reference": {
            "upload_one_file":    "POST /api/upload               — send file, get full analysis",
            "upload_many_files":  "POST /api/upload-multi         — send up to 10 files, get merged timeline",
            "reversal_detection": "POST /api/analyse              — cross-account reversal + roundtrip detection",
            "fifo_audit":         "POST /api/audit                — FIFO + pre-credit balance audit",
            "summary_stats":      "POST /api/summary              — dashboard cards data",
            "all_accounts":       "GET  /api/accounts             — list all uploaded accounts",
            "all_transactions":   "GET  /api/all-transactions     — P2 graph engine endpoint",
            "offline_status":     "GET  /api/cache/status         — check offline mode readiness",
            "offline_fallback":   "GET  /api/cache/{key}          — cached demo data when live API unavailable",
        },
    }
