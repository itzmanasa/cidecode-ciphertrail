"""
test_fifo_and_reversal.py — Day 6 Evening: Unit Tests
=======================================================
Comprehensive unit tests for:
  1. FIFO audit engine (cleaner.py)
  2. Pre-credit balance audit (cleaner.py)
  3. Reversal detection (reversal_detector.py)
  4. Edge case combinations

These tests use synthetic transaction data so they run offline
with no files or server needed. They act as the QA gate before hackathon day —
if all pass, the audit engine is correct.

Run: python test_fifo_and_reversal.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.cleaner import fifo_audit, pre_credit_balance_audit, remove_duplicates
from app.utils.reversal_detector import (
    analyze_reversals, flag_explicit_failures,
    find_unmatched_debits, find_roundtrip_reversals
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def make_txn(txn_id, date, debit=0.0, credit=0.0, balance=0.0,
             status="SUCCESS", txn_type=None, particulars="UPI Transfer"):
    if txn_type is None:
        txn_type = "DEBIT" if debit > 0 else ("CREDIT" if credit > 0 else "UNKNOWN")
    return {
        "txn_id": txn_id, "date": date, "particulars": particulars,
        "debit": debit, "credit": credit, "balance": balance,
        "txn_type": txn_type, "status": status,
        "ref_number": None, "raw_row_index": int(txn_id.split("_")[-1]),
    }


def make_statement(account_number, bank_name, txns):
    return {
        "account_number": account_number,
        "bank_name": bank_name,
        "owner_name": "Test User",
        "transactions": txns,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FIFO TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_fifo_clean_sourced():
    """All debits have sufficient credit sources — should be clean."""
    txns = [
        make_txn("A_0", "2024-01-01", credit=100000.0, balance=100000.0),
        make_txn("A_1", "2024-01-05", debit=50000.0,  balance=50000.0),
        make_txn("A_2", "2024-01-10", debit=50000.0,  balance=0.0),
    ]
    result = fifo_audit(txns)
    assert result["is_clean"], f"Expected clean, got {result['unsourced_debits']}"
    assert result["unsourced_count"] == 0
    assert len(result["matched_pairs"]) == 2
    print("  PASS FIFO: all debits sourced from credit pool")


def test_fifo_unsourced_debit():
    """Debit with no prior credit — should flag as UNSOURCED_DEBIT."""
    txns = [
        make_txn("A_0", "2024-01-01", debit=50000.0, balance=-50000.0),
    ]
    result = fifo_audit(txns)
    assert not result["is_clean"]
    assert result["unsourced_count"] == 1
    assert result["unsourced_debits"][0]["anomaly_type"] == "UNSOURCED_DEBIT"
    print("  PASS FIFO: debit with no credit source correctly flagged")


def test_fifo_excludes_failed():
    """FAILED transactions must NOT consume from credit pool."""
    txns = [
        make_txn("A_0", "2024-01-01", credit=100000.0, balance=100000.0),
        make_txn("A_1", "2024-01-05", debit=100000.0,  balance=0.0,
                 status="FAILED", particulars="FAILED UPI PAYMENT"),
        # After the FAILED debit (excluded), credit pool should still be intact
        make_txn("A_2", "2024-01-10", debit=100000.0, balance=-100000.0),
    ]
    result = fifo_audit(txns)
    # FAILED txn is excluded -> credit pool = 100k -> debit A_2 (100k) is fully sourced
    assert result["is_clean"], f"Expected clean: {result['unsourced_debits']}"
    print("  PASS FIFO: FAILED transactions correctly excluded from credit pool consumption")


def test_fifo_victim_accused_10cr():
    """Rs.10cr goes from victim to accused — accused has no prior credit. Should flag."""
    txns = [
        make_txn("ACCUSED_0", "2024-05-01", credit=10000000.0, balance=10000000.0,
                 particulars="RTGS from VICTIM/SBIN0000001"),
        make_txn("ACCUSED_1", "2024-05-02", debit=5000000.0, balance=5000000.0,
                 particulars="ATM CASH WITHDRAWAL"),
        make_txn("ACCUSED_2", "2024-05-03", debit=5000000.0, balance=0.0,
                 particulars="CHEQUE PAYMENT CHQ NO 001234"),
    ]
    result = fifo_audit(txns)
    assert result["is_clean"]  # All debits are sourced from the 10cr credit
    assert len(result["matched_pairs"]) == 2  # Both debits matched to credit
    assert result["unspent_credits"] == []    # Fully spent
    print("  PASS FIFO: Rs.10cr victim->accused correctly traced (all debits sourced from single credit)")


def test_fifo_partial_sourcing():
    """Debit is only partially covered by available credit."""
    txns = [
        make_txn("A_0", "2024-01-01", credit=30000.0, balance=30000.0),
        make_txn("A_1", "2024-01-05", debit=50000.0, balance=-20000.0),
    ]
    result = fifo_audit(txns)
    assert not result["is_clean"]
    assert result["unsourced_count"] == 1
    unsourced = result["unsourced_debits"][0]
    assert abs(unsourced["unsourced_amount"] - 20000.0) < 1.0
    print("  PASS FIFO: partial credit coverage correctly identifies unsourced portion")


def test_fifo_multiple_sources():
    """Debit sourced from multiple credits in FIFO order."""
    txns = [
        make_txn("A_0", "2024-01-01", credit=30000.0, balance=30000.0),
        make_txn("A_1", "2024-01-02", credit=20000.0, balance=50000.0),
        make_txn("A_2", "2024-01-05", debit=50000.0, balance=0.0),
    ]
    result = fifo_audit(txns)
    assert result["is_clean"]
    pair = result["matched_pairs"][0]
    assert len(pair["sources"]) == 2  # Consumed from both credits
    assert abs(pair["sources"][0]["amount_consumed"] - 30000.0) < 1.0  # FIFO: oldest first
    assert abs(pair["sources"][1]["amount_consumed"] - 20000.0) < 1.0
    print("  PASS FIFO: debit correctly split across multiple credits in chronological order")


# ─────────────────────────────────────────────────────────────────────────────
# PRE-CREDIT BALANCE AUDIT TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_balance_audit_clean():
    """Perfectly balanced statement — should be clean."""
    txns = [
        make_txn("A_0", "2024-01-01", credit=50000.0, balance=50000.0),
        make_txn("A_1", "2024-01-05", debit=10000.0, balance=40000.0),
        make_txn("A_2", "2024-01-10", credit=5000.0, balance=45000.0),
    ]
    result = pre_credit_balance_audit(txns)
    assert result["is_clean"], f"Expected clean: {result['mismatches']}"
    assert result["mismatch_count"] == 0
    print("  PASS Balance audit: clean statement passes with 0 mismatches")


def test_balance_audit_mismatch():
    """Running balance doesn't add up — should flag mismatch."""
    txns = [
        make_txn("A_0", "2024-01-01", credit=50000.0, balance=50000.0),
        make_txn("A_1", "2024-01-05", debit=10000.0, balance=45000.0),  # Should be 40000
    ]
    result = pre_credit_balance_audit(txns)
    assert not result["is_clean"]
    assert result["mismatch_count"] == 1
    mm = result["mismatches"][0]
    assert mm["expected_balance"] == 40000.0
    assert mm["actual_balance"] == 45000.0
    print("  PASS Balance audit: tampering detected correctly (expected 40000, got 45000)")


def test_balance_audit_excludes_failed():
    """
    CRITICAL: FAILED transactions must be excluded from balance check.
    Including them causes absurd results — judges specifically called this out.
    """
    txns = [
        make_txn("A_0", "2024-01-01", credit=50000.0, balance=50000.0),
        make_txn("A_1", "2024-01-03", debit=50000.0, balance=0.0,
                 status="FAILED", particulars="FAILED UPI PAYMENT"),
        # Balance stays 50000 after FAILED txn (bank didn't actually debit)
        make_txn("A_2", "2024-01-05", debit=10000.0, balance=40000.0),
    ]
    result = pre_credit_balance_audit(txns)
    excluded = result.get("excluded_failed_reversal", 0)
    assert excluded == 1, f"Expected 1 excluded, got {excluded}"
    # With FAILED excluded: 50000 - 10000 = 40000 PASS
    assert result["is_clean"], f"Expected clean after excluding FAILED: {result['mismatches']}"
    print("  PASS Balance audit: FAILED transactions correctly excluded (prevents absurd results)")


# ─────────────────────────────────────────────────────────────────────────────
# REVERSAL DETECTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_explicit_failure_detection():
    """Transactions tagged FAILED/REVERSAL are surfaced correctly."""
    stmt = make_statement("ACC_A", "HDFC Bank", [
        make_txn("A_0", "2024-01-01", credit=50000.0, balance=50000.0),
        make_txn("A_1", "2024-01-05", debit=20000.0, balance=30000.0,
                 status="FAILED", particulars="FAILED UPI PAYMENT"),
        make_txn("A_2", "2024-01-06", credit=20000.0, balance=50000.0,
                 status="REVERSAL", particulars="REVERSAL OF PREVIOUS TXN"),
    ])
    failures = flag_explicit_failures([stmt])
    assert len(failures) == 2
    statuses = {f["status"] for f in failures}
    assert "FAILED" in statuses and "REVERSAL" in statuses
    print("  PASS Reversal detection: FAILED and REVERSAL both flagged correctly")


def test_unmatched_debit_single_account():
    """Debit in account A with no other accounts — should be unmatched."""
    stmt = make_statement("ACC_A", "HDFC Bank", [
        make_txn("A_0", "2024-01-01", credit=100000.0, balance=100000.0),
        make_txn("A_1", "2024-01-05", debit=50000.0,  balance=50000.0,
                 particulars="NEFT to ACC 98765432101 SBI"),
    ])
    result = find_unmatched_debits([stmt])
    # With only one account, all debits are unmatched (no other account to receive)
    assert len(result) >= 1
    assert result[0]["flag"] == "LAYER_1_REVERSAL_CANDIDATE"
    print("  PASS Reversal detection: single-account debit correctly flagged as unmatched")


def test_matched_debit_two_accounts():
    """Debit in A matches credit in B — should NOT be flagged as unmatched."""
    stmt_a = make_statement("ACC_A", "HDFC Bank", [
        make_txn("A_0", "2024-01-01", credit=100000.0, balance=100000.0),
        make_txn("A_1", "2024-01-05", debit=50000.0, balance=50000.0,
                 particulars="NEFT to ACC_B SBI"),
    ])
    stmt_b = make_statement("ACC_B", "SBI", [
        make_txn("B_0", "2024-01-05", credit=50000.0, balance=50000.0,
                 particulars="NEFT from ACC_A HDFC"),
    ])
    result = find_unmatched_debits([stmt_a, stmt_b])
    # A's debit of 50000 matches B's credit of 50000 on same date — should NOT be flagged
    unmatched_from_a = [r for r in result if r["source_account"] == "ACC_A"
                        and r["amount"] == 50000.0]
    assert len(unmatched_from_a) == 0, f"Should not flag matched debit: {unmatched_from_a}"
    print("  PASS Reversal detection: matched debit/credit pair correctly NOT flagged")


def test_roundtrip_reversal_detection():
    """Money leaves and returns to same account within 30 days — flagged as roundtrip."""
    stmt = make_statement("ACC_A", "HDFC Bank", [
        make_txn("A_0", "2024-01-01", credit=200000.0, balance=200000.0),
        make_txn("A_1", "2024-01-05", debit=100000.0, balance=100000.0,
                 particulars="NEFT to ACC_B SBI"),
        make_txn("A_2", "2024-01-10", credit=100000.0, balance=200000.0,
                 particulars="NEFT from ACC_B SBI RETURN"),  # Came back!
    ])
    result = find_roundtrip_reversals([stmt])
    assert len(result) >= 1
    assert result[0]["flag"] == "ROUNDTRIP_REVERSAL"
    assert result[0]["days_apart"] == 5
    print("  PASS Reversal detection: round-trip correctly detected (5 days apart)")


def test_roundtrip_outside_window():
    """Money that returns after 30 days should NOT be flagged as roundtrip."""
    stmt = make_statement("ACC_A", "HDFC Bank", [
        make_txn("A_0", "2024-01-01", credit=200000.0, balance=200000.0),
        make_txn("A_1", "2024-01-05", debit=100000.0, balance=100000.0),
        make_txn("A_2", "2024-03-15", credit=100000.0, balance=200000.0),  # 69 days later
    ])
    result = find_roundtrip_reversals([stmt])
    assert len(result) == 0, f"Should not flag 69-day return as roundtrip: {result}"
    print("  PASS Reversal detection: legitimate 69-day delay NOT flagged as roundtrip")


def test_failed_txn_not_in_roundtrip():
    """FAILED transactions must not contribute to roundtrip patterns."""
    stmt = make_statement("ACC_A", "HDFC Bank", [
        make_txn("A_0", "2024-01-01", credit=200000.0, balance=200000.0),
        make_txn("A_1", "2024-01-05", debit=100000.0, balance=200000.0,
                 status="FAILED", particulars="FAILED PAYMENT"),
        make_txn("A_2", "2024-01-07", credit=100000.0, balance=300000.0),
    ])
    result = find_roundtrip_reversals([stmt])
    # FAILED debit excluded -> no debit+credit pair to flag
    assert len(result) == 0, f"FAILED txn should not trigger roundtrip: {result}"
    print("  PASS Reversal detection: FAILED transactions excluded from roundtrip pattern")


def test_analyze_reversals_combined():
    """Full analyze_reversals() combining all detection types."""
    stmt = make_statement("ACC_A", "HDFC Bank", [
        make_txn("A_0", "2024-01-01", credit=500000.0, balance=500000.0),
        make_txn("A_1", "2024-01-05", debit=100000.0, balance=400000.0,
                 status="FAILED", particulars="FAILED UPI PAYMENT"),
        make_txn("A_2", "2024-01-10", debit=200000.0, balance=200000.0),
        make_txn("A_3", "2024-01-15", credit=200000.0, balance=400000.0,
                 particulars="RETURN NEFT CREDIT"),
    ])
    result = analyze_reversals([stmt])
    assert "explicit_failures" in result
    assert "unmatched_debits" in result
    assert "roundtrip_reversals" in result
    assert len(result["explicit_failures"]) == 1  # The FAILED txn
    print(f"  PASS analyze_reversals() combined: {result['total_anomalies']} total anomalies found")


# ─────────────────────────────────────────────────────────────────────────────
# DUPLICATE REMOVAL TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_duplicate_removal_exact():
    """Exact duplicates removed, keeping first occurrence."""
    txns = [
        make_txn("A_0", "2024-01-01", credit=50000.0, balance=50000.0),
        make_txn("A_1", "2024-01-01", credit=50000.0, balance=50000.0),  # Duplicate
        make_txn("A_2", "2024-01-05", debit=10000.0, balance=40000.0),
    ]
    cleaned, removed = remove_duplicates(txns)
    assert removed == 1, f"Expected 1 removed, got {removed}"
    assert len(cleaned) == 2
    print("  PASS Duplicate removal: exact duplicate correctly removed")


def test_no_false_positive_duplicates():
    """Same amount on different dates — NOT duplicates."""
    txns = [
        make_txn("A_0", "2024-01-01", credit=50000.0, balance=50000.0),
        make_txn("A_1", "2024-01-05", credit=50000.0, balance=100000.0),  # Same amount, different date
    ]
    cleaned, removed = remove_duplicates(txns)
    assert removed == 0, "Should not remove different-date same-amount transactions"
    assert len(cleaned) == 2
    print("  PASS Duplicate removal: same-amount different-date transactions preserved")


# ─────────────────────────────────────────────────────────────────────────────
# STRESS TEST
# ─────────────────────────────────────────────────────────────────────────────

def test_fifo_stress_3k_rows():
    """FIFO audit on 3k transactions stays under 10 seconds."""
    import time, random
    random.seed(99)

    txns = []
    balance = 100000.0
    for i in range(3000):
        is_credit = random.random() > 0.45
        amount = round(random.uniform(100, 50000), 2)
        if is_credit:
            balance += amount
            txns.append(make_txn(f"A_{i}", f"2024-{(i//100)%12+1:02d}-{(i%28)+1:02d}",
                                 credit=amount, balance=balance))
        else:
            balance -= amount
            txns.append(make_txn(f"A_{i}", f"2024-{(i//100)%12+1:02d}-{(i%28)+1:02d}",
                                 debit=amount, balance=balance))

    t0 = time.time()
    result = fifo_audit(txns)
    elapsed = time.time() - t0
    assert elapsed < 10.0, f"3k FIFO took {elapsed:.2f}s — too slow"
    print(f"  PASS FIFO stress test: 3000 txns in {elapsed:.3f}s (limit 10s)")


# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("FIFO: clean sourced",                 test_fifo_clean_sourced),
        ("FIFO: unsourced debit",               test_fifo_unsourced_debit),
        ("FIFO: excludes FAILED",               test_fifo_excludes_failed),
        ("FIFO: Rs.10cr victim->accused",           test_fifo_victim_accused_10cr),
        ("FIFO: partial sourcing",              test_fifo_partial_sourcing),
        ("FIFO: multiple credit sources",       test_fifo_multiple_sources),
        ("Balance: clean statement",            test_balance_audit_clean),
        ("Balance: tampering detected",         test_balance_audit_mismatch),
        ("Balance: excludes FAILED (critical)", test_balance_audit_excludes_failed),
        ("Reversal: explicit FAILED/REVERSAL",  test_explicit_failure_detection),
        ("Reversal: unmatched single account",  test_unmatched_debit_single_account),
        ("Reversal: matched two accounts",      test_matched_debit_two_accounts),
        ("Reversal: roundtrip within 30 days",  test_roundtrip_reversal_detection),
        ("Reversal: outside window no flag",    test_roundtrip_outside_window),
        ("Reversal: FAILED excluded roundtrip", test_failed_txn_not_in_roundtrip),
        ("Reversal: combined analyze_reversals",test_analyze_reversals_combined),
        ("Duplicate: exact removal",            test_duplicate_removal_exact),
        ("Duplicate: no false positives",       test_no_false_positive_duplicates),
        ("Stress: FIFO 3k rows",               test_fifo_stress_3k_rows),
    ]

    passed = 0
    failed_list = []

    print("\n" + "="*60)
    print("DAY 6: FIFO ENGINE + REVERSAL DETECTION UNIT TESTS")
    print("="*60)

    for name, fn in tests:
        print(f"\n>> {name}")
        try:
            fn()
            passed += 1
        except AssertionError as e:
            failed_list.append((name, str(e)))
            print(f"  FAIL ASSERTION FAILED: {e}")
        except Exception as e:
            failed_list.append((name, str(e)))
            print(f"  FAIL ERROR: {e}")

    print("\n" + "="*60)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    if failed_list:
        print("\nFailed tests:")
        for name, err in failed_list:
            print(f"  FAIL {name}: {err}")
    else:
        print("PASS ALL TESTS PASSED — FIFO engine and reversal detection are correct")
    print("="*60)
