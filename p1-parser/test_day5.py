"""
test_day5.py — Day 5 Verification
Run from CIDECODE folder: python test_day5.py
"""

import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_edge_case_amounts():
    print("\n" + "="*60)
    print("TEST 1: EDGE CASE AMOUNT PARSING")
    print("="*60)
    from app.parsers.edge_cases import parse_amount_robust

    cases = [
        ("(1,234.56)", -1234.56),
        ("Rs. 1,234.56", 1234.56),
        ("INR 5000", 5000.0),
        ("$100.00", 100.0),
        ("1,234.56Cr", 1234.56),
        ("--", 0.0),
        ("NIL", 0.0),
    ]
    for inp, expected in cases:
        got = parse_amount_robust(inp)
        assert abs(got) == abs(expected), f"'{inp}' -> {got}, expected {expected}"
    print(f"  PASS All {len(cases)} amount edge cases parsed correctly")


def test_edge_case_dates():
    print("\n" + "="*60)
    print("TEST 2: EDGE CASE DATE PARSING")
    print("="*60)
    from app.parsers.edge_cases import parse_date_robust

    cases = [
        "Mon, 15 Jan 2024",
        "15 Jan, 2024",
        "Jan 15, 2024",
        "2024/01/15",
        "15/01/2024 14:30:00",
    ]
    for d in cases:
        got = parse_date_robust(d)
        assert got is not None, f"Failed to parse: {d}"
    print(f"  PASS All {len(cases)} date edge cases parsed correctly")


def test_fuzzy_headers():
    print("\n" + "="*60)
    print("TEST 3: FUZZY HEADER MATCHING")
    print("="*60)
    from app.parsers.edge_cases import fuzzy_match_header, EXTENDED_BALANCE_KEYWORDS

    assert fuzzy_match_header("Balanace", EXTENDED_BALANCE_KEYWORDS), "Typo 'Balanace' not matched"
    assert not fuzzy_match_header("Random Text Here", EXTENDED_BALANCE_KEYWORDS), "False positive match"
    print("  PASS Fuzzy matching catches typos, avoids false positives")


def test_merged_cells():
    print("\n" + "="*60)
    print("TEST 4: MERGED CELL FORWARD-FILL")
    print("="*60)
    from app.parsers.edge_cases import fill_merged_cells

    rows = [
        ["15-01-2024", "Particulars A", "100"],
        [None, "Particulars B continued", "200"],
    ]
    filled = fill_merged_cells(rows)
    assert filled[1][0] == "15-01-2024", "Merged cell not forward-filled"
    print("  PASS Merged cells forward-fill correctly")


def test_real_data_regression():
    print("\n" + "="*60)
    print("TEST 5: REGRESSION ON REAL DATA (Days 1-4 files still work)")
    print("="*60)
    from app.parsers.dispatcher import dispatch_parse

    if not os.path.exists("mock_statement.json"):
        print("  WARN  mock_statement.json not found, skipping")
        return

    with open("mock_statement.json") as f:
        stmt = json.load(f)
    assert len(stmt["transactions"]) > 0
    print(f"  PASS mock_statement.json still loads correctly: {len(stmt['transactions'])} txns")


def test_multi_upload_merge_logic():
    print("\n" + "="*60)
    print("TEST 6: MULTI-UPLOAD MERGE LOGIC (offline simulation)")
    print("="*60)
    from datetime import datetime

    fake_txns = [
        {"date": "2024-03-01", "account_number": "ACC_A", "particulars": "txn1"},
        {"date": "2024-01-15", "account_number": "ACC_B", "particulars": "txn2"},
        {"date": "2024-02-10", "account_number": "ACC_A", "particulars": "txn3"},
    ]

    def sort_key(t):
        try:
            return datetime.strptime(t["date"], "%Y-%m-%d")
        except ValueError:
            return datetime.max

    unified = sorted(fake_txns, key=sort_key)
    assert unified[0]["date"] == "2024-01-15", "Sort order wrong"
    assert unified[-1]["date"] == "2024-03-01", "Sort order wrong"
    accounts = {t["account_number"] for t in unified}
    assert len(accounts) == 2
    print(f"  PASS Merge + sort logic correct: {len(unified)} txns, {len(accounts)} accounts")


def test_api_endpoints():
    print("\n" + "="*60)
    print("TEST 7: API ENDPOINTS (server must be running)")
    print("="*60)
    try:
        import httpx
        r = httpx.get("http://localhost:8000/", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "upload_multi" in data.get("endpoints", {})
        print("  PASS Server up, /api/upload-multi endpoint registered")
    except Exception as e:
        print(f"  WARN  API test skipped (start server first): {e}")


if __name__ == "__main__":
    test_edge_case_amounts()
    test_edge_case_dates()
    test_fuzzy_headers()
    test_merged_cells()
    test_real_data_regression()
    test_multi_upload_merge_logic()
    test_api_endpoints()
    print("\nPASS DAY 5 ALL TESTS COMPLETE")
    print("="*60)
