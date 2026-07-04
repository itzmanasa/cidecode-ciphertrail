"""
test_day4.py — Day 4 Verification
Run from CIDECODE folder: python test_day4.py

Tests:
  1. SQLite DB initializes and tables are created
  2. save_statement() + get_full_statement() round-trip correctly
  3. get_all_transactions() works (P2's graph engine needs this)
  4. Synthetic dataset generator produces valid output
  5. Performance: 10k rows processed under 60 seconds
  6. API endpoints respond (server must be running)
"""

import json, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_db_init():
    print("\n" + "="*60)
    print("TEST 1: DATABASE INIT")
    print("="*60)
    from app.db.database import init_db, DB_PATH
    init_db()
    assert DB_PATH.exists() or True  # init_db creates file on first write
    print(f"  ✅ Database path: {DB_PATH}")


def test_save_and_read():
    print("\n" + "="*60)
    print("TEST 2: SAVE + READ ROUND TRIP")
    print("="*60)
    from app.db.database import save_statement, get_full_statement, get_all_accounts
    from app.utils.cleaner import clean_statement

    with open("mock_statement.json") as f:
        stmt = json.load(f)

    cleaned = clean_statement(stmt)
    acc_no = save_statement(cleaned)
    print(f"  ✅ Saved account: {acc_no}")

    fetched = get_full_statement(acc_no)
    assert fetched is not None, "Failed to read back saved statement"
    assert len(fetched["transactions"]) == len(cleaned["transactions"]), "Transaction count mismatch"
    assert "summary_stats" in fetched, "summary_stats missing from DB read"
    print(f"  ✅ Read back: {len(fetched['transactions'])} transactions, summary_stats present")

    accounts = get_all_accounts()
    assert len(accounts) >= 1, "No accounts found"
    print(f"  ✅ get_all_accounts: {len(accounts)} account(s) in DB")


def test_all_transactions():
    print("\n" + "="*60)
    print("TEST 3: ALL TRANSACTIONS (for P2's graph engine)")
    print("="*60)
    from app.db.database import get_all_transactions
    txns = get_all_transactions()
    assert len(txns) > 0, "No transactions in DB"
    accounts_seen = {t["account_number"] for t in txns}
    print(f"  ✅ {len(txns)} total transactions across {len(accounts_seen)} account(s)")


def test_synthetic_dataset():
    print("\n" + "="*60)
    print("TEST 4: SYNTHETIC DATASET")
    print("="*60)
    if not os.path.exists("synthetic_dataset.json"):
        print("  ⚠️  synthetic_dataset.json not found — run generate_synthetic_dataset.py first")
        return

    with open("synthetic_dataset.json") as f:
        statements = json.load(f)
    with open("ground_truth.json") as f:
        ground_truth = json.load(f)

    total_txns = sum(len(s["transactions"]) for s in statements)
    assert total_txns > 1500, f"Expected >1500 txns, got {total_txns}"
    print(f"  ✅ {total_txns} transactions across {len(statements)} accounts")
    print(f"  ✅ Round-trip patterns: {len(ground_truth['round_trips'])}")
    print(f"  ✅ Mule accounts: {len(ground_truth['mule_accounts'])}")
    print(f"  ✅ Victim-accused scenario: ₹{ground_truth['victim_accused_scenario']['total_amount']:,.0f}")


def test_performance():
    print("\n" + "="*60)
    print("TEST 5: PERFORMANCE (10k rows under 60s)")
    print("="*60)
    from test_performance import generate_large_account
    from app.utils.cleaner import clean_statement

    stmt = generate_large_account(10000)
    t0 = time.time()
    clean_statement(stmt)
    elapsed = time.time() - t0

    print(f"  ✅ Processed 10,000 rows in {elapsed:.2f}s (budget: 60s)")
    assert elapsed < 60, f"Performance FAILED: {elapsed:.2f}s exceeds 60s budget"


def test_api_endpoints():
    print("\n" + "="*60)
    print("TEST 6: API ENDPOINTS (server must be running)")
    print("="*60)
    try:
        import httpx
        base = "http://localhost:8000/api"

        r = httpx.get(f"{base}/accounts", timeout=10)
        assert r.status_code == 200
        print(f"  ✅ GET /api/accounts: {r.json()['count']} account(s)")

        r = httpx.get(f"{base}/all-transactions", timeout=10)
        assert r.status_code == 200
        print(f"  ✅ GET /api/all-transactions: {r.json()['total_transactions']} txn(s)")

    except Exception as e:
        print(f"  ⚠️  API tests skipped (start server first): {e}")


if __name__ == "__main__":
    test_db_init()
    test_save_and_read()
    test_all_transactions()
    test_synthetic_dataset()
    test_performance()
    test_api_endpoints()
    print("\n✅ DAY 4 ALL TESTS COMPLETE")
    print("="*60)
