"""
cache_routes.py — GET /api/cache/{key} (Day 7)
P3 calls these when the live API fails. Returns pre-cached demo responses.
Also exposes a cache status endpoint so P3 knows what's available offline.
"""

from fastapi import APIRouter, HTTPException
from offline_cache import cache_read, cache_exists, CACHE_DIR

router = APIRouter()

VALID_KEYS = ["accounts", "all_transactions", "summary_demo",
              "analyse_demo", "audit_demo"]


@router.get("/cache/status")
def cache_status():
    """Check which cached responses are available for offline mode."""
    available = {}
    for key in VALID_KEYS:
        if cache_exists(key):
            data = cache_read(key)
            available[key] = {
                "available": True,
                "cached_at": data.get("_cached_at"),
                "endpoint_equivalent": f"/api/{key.replace('_', '-').replace('-demo', '')}",
            }
        else:
            available[key] = {"available": False}

    return {
        "offline_mode_ready": all(v.get("available") for v in available.values()),
        "cache_directory": str(CACHE_DIR),
        "keys": available,
    }


@router.get("/cache/{key}")
def get_cached_response(key: str):
    """
    Return a pre-cached API response.
    P3 usage: if /api/accounts fails, call /api/cache/accounts instead.
    """
    if key not in VALID_KEYS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown cache key '{key}'. Valid keys: {VALID_KEYS}"
        )
    if not cache_exists(key):
        raise HTTPException(
            status_code=503,
            detail=f"Cache for '{key}' not built yet. Run: python offline_cache.py"
        )
    return cache_read(key)
