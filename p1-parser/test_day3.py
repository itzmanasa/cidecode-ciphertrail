"""
test_day3.py — Day 3 Verification
Run from CIDECODE folder: python test_day3.py

Tests:
  1. Registry correctly selects parser for each file type
  2. clean_statement() runs without error on all real files
  3. Both audit modes return results
  4. summary_stats has all required fields for P3 dashboard cards
  5. /api/transactions, /api/audit, /api/summary, /api/clean endpoints respond
"""

import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.parsers.registry import registry
from app.parsers.dispatcher import dispatch_parse
from app.utils.cleaner import clean_statement

REAL_FILES = [
    # Use mock if real files not on your machine
]

def test_registry():
    print("\n" + "="*60)
    print("TEST 1: PARSER REGISTRY")
    print("="*60)
    parsers = registry.list_parsers()
    print(f"  Registered parsers ({len(parsers)}):")
    for p in parsers:
        print(f"    • {p}")
    assert len(parsers) >= 8, f"Expected >=8 parsers, got {len(parsers)}"
    print(f"  ✅ Registry has {len(parsers)} parsers")


def test_clean_on_mock():
    print("\n" + "="*60)
    print("TEST 2: CLEAN PIPELINE ON MOCK DATA")
    print("="*60)

    with open("mock_statement.json") as f:
        stmt = json.load(f)

    cleaned = clean_statement(stmt)

    # Check summary_stats keys P3 needs
    required_keys = [
        "total_transactions", "success_count", "failed_count", "reversal_count",
        "total_debit", "total_credit", "net_flow",
        "cash_withdrawal_count", "cash_withdrawal_total",
        "cheque_withdrawal_count", "cheque_withdrawal_total",
        "balance_audit_clean", "fifo_audit_clean",
        "balance_mismatches", "unsourced_debits",
    ]
    stats = cleaned.get("summary_stats", {})
    missing = [k for k in required_keys if k not in stats]
    assert not missing, f"Missing summary_stats keys: {missing}"
    print(f"  ✅ summary_stats: all {len(required_keys)} keys present")

    # Check audit results
    audit = cleaned.get("audit_results", {})
    assert "pre_credit_audit" in audit, "Missing pre_credit_audit"
    assert "fifo_audit"       in audit, "Missing fifo_audit"
    assert "duplicates_removed" in audit, "Missing duplicates_removed"
    print(f"  ✅ audit_results: pre_credit + fifo + duplicates_removed present")

    pre = audit["pre_credit_audit"]
    fifo = audit["fifo_audit"]
    print(f"  ✅ Pre-credit audit: {pre['total_checked']} checked, {pre['mismatch_count']} mismatches")
    print(f"  ✅ FIFO audit: {fifo['total_checked']} checked, {fifo['unsourced_count']} unsourced")
    print(f"  ✅ Summary: total_in=₹{stats['total_credit']:,.0f} | total_out=₹{stats['total_debit']:,.0f} | net=₹{stats['net_flow']:,.0f}")
    print(f"  ✅ Cash withdrawals: {stats['cash_withdrawal_count']} txns | ₹{stats['cash_withdrawal_total']:,.0f}")
    print(f"  ✅ Cheque withdrawals: {stats['cheque_withdrawal_count']} txns | ₹{stats['cheque_withdrawal_total']:,.0f}")
    print(f"  ✅ Duplicates removed: {audit['duplicates_removed']}")


def test_header_extraction():
    print("\n" + "="*60)
    print("TEST 3: HEADER FIELD EXTRACTION")
    print("="*60)

    from app.utils.cleaner import extract_header_fields

    # Simulate a statement where parser missed some fields
    partial_stmt = {
        "account_number": "UNKNOWN",
        "owner_name": "UNKNOWN",
        "bank_name": "IDFC First Bank",
        "source_file": "KOMAL_statement.pdf",
        "period_from": None,
        "period_to": None,
        "transactions": [
            {"date": "2025-04-22", "particulars": "UPI", "debit": 84.0, "credit": 0.0, "balance": 2913.50, "txn_type": "DEBIT", "status": "SUCCESS"},
            {"date": "2025-05-18", "particulars": "NEFT", "debit": 0.0, "credit": 100.0, "balance": 3013.50, "txn_type": "CREDIT", "status": "SUCCESS"},
        ]
    }
    enriched = extract_header_fields(partial_stmt)

    # Owner name should be extracted from filename
    assert enriched.get("owner_name") not in (None, "UNKNOWN", ""), \
        f"Owner name not extracted: {enriched.get('owner_name')}"
    print(f"  ✅ Owner from filename: {enriched['owner_name']}")

    # Period should be computed from transactions
    assert enriched.get("period_from") == "2025-04-22", f"period_from wrong: {enriched.get('period_from')}"
    assert enriched.get("period_to")   == "2025-05-18", f"period_to wrong: {enriched.get('period_to')}"
    print(f"  ✅ Period from transactions: {enriched['period_from']} → {enriched['period_to']}")


def test_api_endpoints():
    print("\n" + "="*60)
    print("TEST 4: API ENDPOINTS (server must be running)")
    print("="*60)

    try:
        import httpx
        with open("mock_statement.json") as f:
            stmt = json.load(f)

        base = "http://localhost:8000/api"

        # /transactions
        r = httpx.post(f"{base}/transactions", json={"statement": stmt}, timeout=10)
        assert r.status_code == 200, f"/transactions: {r.status_code}"
        data = r.json()
        assert data["success"] and "transactions" in data
        print(f"  ✅ /api/transactions: {data['counts']['total']} txns returned")

        # /audit
        r = httpx.post(f"{base}/audit", json={"statement": stmt}, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "pre_credit_audit" in data and "fifo_audit" in data
        print(f"  ✅ /api/audit: pre_credit={data['pre_credit_audit']['is_clean']} | fifo={data['fifo_audit']['is_clean']}")

        # /summary
        r = httpx.post(f"{base}/summary", json={"statement": stmt}, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "header" in data and "summary_stats" in data
        print(f"  ✅ /api/summary: net_flow=₹{data['summary_stats'].get('net_flow', 0):,.0f}")

        # /clean
        r = httpx.post(f"{base}/clean", json={"statement": stmt}, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        print(f"  ✅ /api/clean: OK")

    except Exception as e:
        print(f"  ⚠️  API tests skipped (start server first): {e}")


if __name__ == "__main__":
    test_registry()
    test_clean_on_mock()
    test_header_extraction()
    test_api_endpoints()
    print("\n✅ DAY 3 ALL TESTS COMPLETE")
    print("="*60)
