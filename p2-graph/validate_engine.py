import json
import pandas as pd
from graph_engine import build_transaction_graph, detect_round_trips, flag_suspicious_nodes
from analytics import generate_analytics


def load_synthetic_dataset(path: str) -> pd.DataFrame:
    """Load P1's synthetic dataset JSON into a DataFrame."""
    from adapter import adapt_multiple_statements, adapt_statement_to_engine

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # P1's format is a list of BankStatement objects
    if isinstance(data, list):
        # Each item is a full BankStatement with account_number + transactions
        return adapt_multiple_statements(data)
    elif isinstance(data, dict) and "transactions" in data:
        # Single statement
        return adapt_statement_to_engine(data)
    else:
        print(f"Unknown format — keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        return pd.DataFrame()


def load_ground_truth(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_against_ground_truth(findings: dict, ground_truth: dict):
    print("\n" + "="*60)
    print("VALIDATION AGAINST GROUND TRUTH")
    print("="*60)

    # Round trips
    your_round_trips = findings.get("round_trips", [])
    expected_round_trips = ground_truth.get("round_trips",
                          ground_truth.get("expected_round_trips", []))

    print(f"\nRound Trips:")
    print(f"  Your engine found : {len(your_round_trips)}")
    print(f"  Ground truth says : {len(expected_round_trips)}")

    if len(your_round_trips) >= len(expected_round_trips):
        print("  ✅ Round trip count matches or exceeds ground truth")
    else:
        print("  ⚠️  Fewer round trips than expected — may need tuning")

    # Reversals
    your_reversals = findings.get("analytics", {}).get("reversal_count", 0)
    expected_reversals = ground_truth.get("reversal_count",
                        ground_truth.get("expected_reversals", 0))

    print(f"\nReversals:")
    print(f"  Your engine found : {your_reversals}")
    print(f"  Ground truth says : {expected_reversals}")

    if your_reversals == expected_reversals:
        print("  ✅ Reversal count matches")
    else:
        print("  ⚠️  Reversal count mismatch")

    # High risk accounts
    your_flags = findings.get("node_flags", {})
    your_high_risk = [acc for acc, info in your_flags.items()
                     if info.get("risk") == "HIGH"]

    raw_mules = ground_truth.get("mule_accounts",
                ground_truth.get("expected_mules", []))

    # Handle case where mules are dicts instead of strings
    if raw_mules and isinstance(raw_mules[0], dict):
        expected_mules = [m.get("account_number", "") for m in raw_mules]
    else:
        expected_mules = raw_mules

    print(f"\nHigh Risk / Mule Accounts:")
    print(f"  Your engine flagged : {your_high_risk}")
    print(f"  Ground truth says   : {expected_mules}")

    matched = set(your_high_risk) & set(expected_mules)
    missed = set(expected_mules) - set(your_high_risk)

    if matched:
        print(f"  ✅ Correctly identified: {list(matched)}")
    if missed:
        print(f"  ⚠️  Missed mules: {list(missed)}")

    print("\n" + "="*60)


if __name__ == "__main__":
    import time
    from findings import get_full_findings

    # Test 1 — Synthetic dataset
    print("Loading synthetic_dataset.json...")
    try:
        df = load_synthetic_dataset("synthetic_dataset.json")
        print(f"Loaded {len(df)} transactions")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Sample row:\n{df.iloc[0]}")

        print("\nRunning engine on synthetic dataset...")
        start = time.time()
        findings = get_full_findings(df)
        elapsed = time.time() - start

        print(f"Engine completed in {elapsed:.2f}s")
        print(f"Round trips found: {len(findings['round_trips'])}")
        print(f"Total amount moved: Rs.{findings['analytics']['total_amount_moved']:,.0f}")
        print(f"Reversals excluded: {findings['analytics']['reversal_count']}")

    except Exception as e:
        print(f"Error loading synthetic dataset: {e}")
        findings = {}

    # Test 2 — Ground truth validation
    print("\nLoading ground_truth.json...")
    try:
        ground_truth = load_ground_truth("ground_truth.json")
        print(f"Ground truth keys: {list(ground_truth.keys())}")
        validate_against_ground_truth(findings, ground_truth)
    except Exception as e:
        print(f"Error loading ground truth: {e}")

    # Test 3 — Round trip heavy dataset
    print("\nLoading demo_set_3_roundtrip_heavy.json...")
    try:
        df_heavy = load_synthetic_dataset("demo_set_3_roundtrip_heavy.json")
        print(f"Loaded {len(df_heavy)} transactions")

        start = time.time()
        findings_heavy = get_full_findings(df_heavy)
        elapsed = time.time() - start

        print(f"Engine completed in {elapsed:.2f}s")
        print(f"Round trips found: {len(findings_heavy['round_trips'])}")
        for rt in findings_heavy['round_trips'][:5]:
            print(f"  {rt['cycle_str']}")
            print(f"  Amount: Rs.{rt['total_amount']:,} | Layers: {rt['layer']}")

    except Exception as e:
        print(f"Error loading round trip heavy dataset: {e}")