"""
offline_cache.py — Day 7 Afternoon: Offline Mode
==================================================
Pre-caches responses for all key API endpoints so the demo works
even if the server crashes or there's no internet on hackathon day.

On startup, the server checks if cached responses exist and updates them.
P3's frontend can detect a failed API call and fall back to these cached
JSON files automatically.

Cache files are stored in cache/ directory — commit these to git before
the hackathon so they're available even if the server can't start.

Run standalone to regenerate the cache:
    python offline_cache.py
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def cache_write(key: str, data: dict):
    path = CACHE_DIR / f"{key}.json"
    data["_cached_at"] = datetime.now().isoformat()
    data["_is_cached"] = True
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Cached: {path}")


def cache_read(key: str) -> dict:
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def cache_exists(key: str) -> bool:
    return (CACHE_DIR / f"{key}.json").exists()


def build_full_cache():
    """
    Build all cache files from the demo datasets.
    Run this before the hackathon to ensure offline mode works.
    """
    print(f"Building offline cache in {CACHE_DIR}/...")

    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    from app.utils.cleaner import clean_statement
    from app.utils.reversal_detector import analyze_reversals

    # ── Cache 1: /api/accounts ────────────────────────────────────────────────
    accounts_preview = []
    for demo_file in ["demo_set_1_simple.json", "demo_set_2_medium.json",
                      "demo_set_3_roundtrip_heavy.json"]:
        if not Path(demo_file).exists():
            continue
        with open(demo_file) as f:
            stmts = json.load(f)
        for s in stmts:
            accounts_preview.append({
                "account_number": s["account_number"],
                "bank_name": s["bank_name"],
                "owner_name": s["owner_name"],
                "period_from": s.get("period_from"),
                "period_to": s.get("period_to"),
                "source_file": s["source_file"],
            })

    cache_write("accounts", {
        "success": True,
        "count": len(accounts_preview),
        "accounts": accounts_preview,
    })
    print(f"  ✅ /api/accounts → {len(accounts_preview)} accounts cached")

    # ── Cache 2: /api/all-transactions ────────────────────────────────────────
    all_txns = []
    for demo_file in ["demo_set_3_roundtrip_heavy.json"]:
        if not Path(demo_file).exists():
            continue
        with open(demo_file) as f:
            stmts = json.load(f)
        for s in stmts:
            for t in s["transactions"]:
                t2 = dict(t)
                t2["account_number"] = s["account_number"]
                t2["bank_name"] = s["bank_name"]
                all_txns.append(t2)

    cache_write("all_transactions", {
        "success": True,
        "total_transactions": len(all_txns),
        "account_count": len({t["account_number"] for t in all_txns}),
        "transactions": all_txns,
    })
    print(f"  ✅ /api/all-transactions → {len(all_txns)} transactions cached")

    # ── Cache 3: /api/summary for demo account ────────────────────────────────
    if Path("demo_set_3_roundtrip_heavy.json").exists():
        with open("demo_set_3_roundtrip_heavy.json") as f:
            stmts = json.load(f)
        demo_stmt = stmts[0]  # First account as demo
        cleaned = clean_statement(demo_stmt)
        cache_write("summary_demo", {
            "success": True,
            "header": {
                "account_number": cleaned["account_number"],
                "bank_name": cleaned["bank_name"],
                "owner_name": cleaned["owner_name"],
                "period_from": cleaned.get("period_from"),
                "period_to": cleaned.get("period_to"),
            },
            "summary_stats": cleaned.get("summary_stats", {}),
        })
        stats = cleaned.get("summary_stats", {})
        print(f"  ✅ /api/summary (demo) → total_in=₹{stats.get('total_credit',0):,.0f} cached")

    # ── Cache 4: /api/analyse — reversal detection on demo set 3 ─────────────
    if Path("demo_set_3_roundtrip_heavy.json").exists():
        with open("demo_set_3_roundtrip_heavy.json") as f:
            stmts = json.load(f)
        anomalies = analyze_reversals(stmts)
        cache_write("analyse_demo", {
            "success": True,
            "statements_analysed": len(stmts),
            "anomaly_report": anomalies,
        })
        print(f"  ✅ /api/analyse (demo) → {anomalies['total_anomalies']} anomalies cached")

    # ── Cache 5: FIFO audit on demo ───────────────────────────────────────────
    if Path("demo_set_2_medium.json").exists():
        with open("demo_set_2_medium.json") as f:
            stmts = json.load(f)
        stmt = stmts[0]
        from app.utils.cleaner import fifo_audit, pre_credit_balance_audit
        fifo = fifo_audit(stmt["transactions"])
        bal  = pre_credit_balance_audit(stmt["transactions"])
        cache_write("audit_demo", {
            "success": True,
            "account_number": stmt["account_number"],
            "pre_credit_audit": bal,
            "fifo_audit": fifo,
            "overall_clean": bal["is_clean"] and fifo["is_clean"],
        })
        print(f"  ✅ /api/audit (demo) → pre_credit={bal['is_clean']}, fifo={fifo['is_clean']} cached")

    print(f"\n✅ Offline cache built. {len(list(CACHE_DIR.glob('*.json')))} files in {CACHE_DIR}/")
    print("   Commit the cache/ folder to git before the hackathon.")


if __name__ == "__main__":
    build_full_cache()
