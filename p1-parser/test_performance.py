"""
test_performance.py — Day 4 Evening: Performance Test
========================================================
Hackathon requirement: parse 10k rows under 60 seconds.

Generates a single large synthetic account with 10,000 transactions,
runs it through the FULL pipeline (parse-equivalent → clean → audit),
and times it.

Run: python test_performance.py
"""

import time
import json
import sys
import os
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.cleaner import clean_statement

random.seed(7)


def generate_large_account(num_txns=10000):
    """Generate one account with num_txns transactions for stress testing."""
    account_number = "9999900001234567"
    transactions = []
    balance = 100000.0
    base_date = datetime(2024, 1, 1)

    for i in range(num_txns):
        date = base_date + timedelta(hours=i * 2)  # Spread across ~2.3 years
        is_debit = random.random() > 0.45
        amount = round(random.uniform(100, 100000), 2)

        if is_debit:
            balance -= amount
            debit, credit = amount, 0.0
            txn_type = "DEBIT"
        else:
            balance += amount
            debit, credit = 0.0, amount
            txn_type = "CREDIT"

        status = "SUCCESS"
        if random.random() < 0.02:  # 2% failed/reversal noise
            status = random.choice(["FAILED", "REVERSAL"])

        transactions.append({
            "txn_id": f"{account_number}_{i:05d}",
            "date": date.strftime("%Y-%m-%d"),
            "particulars": f"UPI/{random.randint(100000000000,999999999999)}/Transaction {i}",
            "debit": round(debit, 2),
            "credit": round(credit, 2),
            "balance": round(balance, 2),
            "txn_type": txn_type,
            "status": status,
            "ref_number": f"REF{random.randint(100000,999999)}",
            "raw_row_index": i,
        })

    return {
        "account_number": account_number,
        "bank_name": "Stress Test Bank",
        "owner_name": "Performance Test Account",
        "branch": None, "ifsc": None, "email": None,
        "period_from": base_date.strftime("%Y-%m-%d"),
        "period_to": (base_date + timedelta(hours=num_txns*2)).strftime("%Y-%m-%d"),
        "opening_balance": 100000.0,
        "closing_balance": balance,
        "source_file": "performance_test.json",
        "parse_method": "synthetic_stress_test",
        "transactions": transactions,
        "parse_warnings": [],
    }


def run_performance_test():
    print("="*60)
    print("DAY 4 PERFORMANCE TEST: 10,000 rows under 60 seconds")
    print("="*60)

    print("\nGenerating 10,000 synthetic transactions...")
    t0 = time.time()
    statement = generate_large_account(10000)
    gen_time = time.time() - t0
    print(f"  Generation took: {gen_time:.2f}s (not counted toward the 60s budget)")

    print("\nRunning full clean_statement() pipeline (dedup + audit + stats)...")
    t1 = time.time()
    cleaned = clean_statement(statement)
    process_time = time.time() - t1

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"  Transactions processed: {len(statement['transactions']):,}")
    print(f"  Processing time:        {process_time:.2f} seconds")
    print(f"  Budget:                 60.00 seconds")
    print(f"  Duplicates removed:     {cleaned['audit_results']['duplicates_removed']}")
    print(f"  Balance mismatches:     {cleaned['audit_results']['pre_credit_audit']['mismatch_count']}")
    print(f"  FIFO unsourced debits:  {cleaned['audit_results']['fifo_audit']['unsourced_count']}")
    print(f"  Throughput:             {len(statement['transactions'])/process_time:,.0f} txns/sec")

    passed = process_time < 60.0
    print(f"\n{'✅ PASSED' if passed else '❌ FAILED'} — "
          f"{'within' if passed else 'EXCEEDS'} the 60 second budget")

    assert passed, f"Performance test FAILED: took {process_time:.2f}s, budget is 60s"
    print("="*60)


if __name__ == "__main__":
    run_performance_test()
