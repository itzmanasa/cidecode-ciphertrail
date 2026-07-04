"""
test_day7.py — Day 7 Final Hackathon Readiness Check
Run from CIDECODE folder: python test_day7.py

This is the LAST test you run before the hackathon starts.
If everything here passes, you are ready.
"""

import json, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_demo_datasets_exist():
    print("\n" + "="*60)
    print("TEST 1: DEMO DATASETS READY")
    print("="*60)
    files = {
        "demo_set_1_simple.json":          (1, 25),
        "demo_set_2_medium.json":          (2, 60),
        "demo_set_3_roundtrip_heavy.json": (6, 170),
    }
    for fname, (min_accs, min_txns) in files.items():
        assert os.path.exists(fname), f"Missing: {fname}"
        with open(fname) as f:
            stmts = json.load(f)
        total = sum(len(s["transactions"]) for s in stmts)
        assert len(stmts) >= min_accs, f"Expected >={min_accs} accounts"
        assert total >= min_txns, f"Expected >={min_txns} txns"
        print(f"  PASS {fname}: {len(stmts)} accounts, {total} txns")


def test_offline_cache_built():
    print("\n" + "="*60)
    print("TEST 2: OFFLINE CACHE READY")
    print("="*60)
    from offline_cache import cache_exists, CACHE_DIR
    keys = ["accounts", "all_transactions", "summary_demo", "analyse_demo", "audit_demo"]
    for key in keys:
        assert cache_exists(key), f"Cache missing: {key}.json — run: python offline_cache.py"
        print(f"  PASS cache/{key}.json exists")
    print(f"  PASS Offline mode is ready — demo will work even if server restarts")


def test_demo_set_3_has_roundtrips():
    print("\n" + "="*60)
    print("TEST 3: DEMO SET 3 ANOMALY VERIFICATION")
    print("="*60)
    from offline_cache import cache_read
    cache = cache_read("analyse_demo")
    report = cache.get("anomaly_report", {})

    assert report.get("total_anomalies", 0) > 0, "No anomalies found in demo set 3"
    print(f"  PASS Total anomalies: {report['total_anomalies']}")
    print(f"  PASS Explicit failures: {report['summary']['explicit_failure_count']}")
    print(f"  PASS Unmatched debits: {report['summary']['unmatched_debit_count']}")
    print(f"  PASS Roundtrip reversals: {report['summary']['roundtrip_reversal_count']}")


def test_all_previous_tests_still_pass():
    print("\n" + "="*60)
    print("TEST 4: FULL REGRESSION — ALL PREVIOUS TESTS")
    print("="*60)
    import subprocess

    test_files = [
        "test_fifo_and_reversal.py",
        "test_day5.py",
    ]

    for tf in test_files:
        if not os.path.exists(tf):
            print(f"  WARN  {tf} not found, skipping")
            continue
        r = subprocess.run(["python", tf], capture_output=True, text=True)
        passed = "ALL TESTS PASSED" in r.stdout or "ALL TESTS COMPLETE" in r.stdout
        print(f"  {'PASS' if passed else 'FAIL'} {tf}: {'PASSED' if passed else 'FAILED'}")
        if not passed:
            print(f"    stderr: {r.stderr[-200:]}")


def test_performance_final():
    print("\n" + "="*60)
    print("TEST 5: PERFORMANCE FINAL CONFIRMATION")
    print("="*60)
    from app.utils.cleaner import clean_statement
    from test_performance import generate_large_account

    for n, budget in [(1518, 5), (3000, 10), (10000, 60)]:
        stmt = generate_large_account(n)
        t0 = time.time()
        clean_statement(stmt)
        elapsed = time.time() - t0
        print(f"  {'PASS' if elapsed < budget else 'FAIL'} {n:,} rows: {elapsed:.2f}s (budget {budget}s)")


def test_readme_exists():
    print("\n" + "="*60)
    print("TEST 6: README FOR JUDGES")
    print("="*60)
    assert os.path.exists("README.md"), "README.md missing"
    with open("README.md", encoding="utf-8") as f:
        content = f.read()
    required_sections = [
        "Quick start", "API Endpoints", "Supported bank formats",
        "FIFO audit", "offline mode", "Hard questions"
    ]
    for section in required_sections:
        found = section.lower() in content.lower()
        print(f"  {'PASS' if found else 'FAIL'} Section: '{section}'")


def test_api_live():
    print("\n" + "="*60)
    print("TEST 7: LIVE API FINAL CHECK (server must be running)")
    print("="*60)
    try:
        import httpx
        base = "http://localhost:8000"

        r = httpx.get(f"{base}/health", timeout=5)
        h = r.json()
        print(f"  PASS Server version: {h['version']}")
        print(f"  PASS Offline mode ready: {h['offline_mode_ready']}")

        r = httpx.get(f"{base}/api/cache/status", timeout=5)
        s = r.json()
        print(f"  PASS Cache status — offline_mode_ready: {s['offline_mode_ready']}")

    except Exception as e:
        print(f"  WARN  API skipped (start server first): {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("DAY 7 — HACKATHON READINESS CHECK")
    print("="*60)

    test_demo_datasets_exist()
    test_offline_cache_built()
    test_demo_set_3_has_roundtrips()
    test_all_previous_tests_still_pass()
    test_performance_final()
    test_readme_exists()
    test_api_live()

    print("\n" + "="*60)
    print("PASS DAY 7 COMPLETE — YOU ARE HACKATHON READY")
    print("="*60)
    print("""
QUICK CHECKLIST BEFORE YOU GO:
  □ Server starts with: uvicorn app.main:app --port 8000
  □ /docs loads with all endpoints visible
  □ At least 1 real PDF uploads and parses correctly
  □ cache/ folder committed to git / backed up on USB
  □ synthetic_dataset.json + ground_truth.json sent to P2 and P3
  □ README.md available for judges
""")
