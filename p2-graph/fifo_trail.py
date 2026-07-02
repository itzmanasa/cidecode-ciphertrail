import pandas as pd
from collections import deque


def trace_fifo_trail(df: pd.DataFrame, target_account: str) -> dict:
    account_txns = df[
        (df["is_reversal"] == False) &
        ((df["from_account"] == target_account) |
         (df["to_account"] == target_account))
    ].sort_values("date").copy()

    credit_queue = deque()
    trail = []

    for _, row in account_txns.iterrows():
        is_credit = row["to_account"] == target_account
        is_debit = row["from_account"] == target_account

        if is_credit:
            credit_queue.append({
                "amount": row["amount"],
                "source": row["from_account"],
                "date": row["date"],
                "txn_id": row["txn_id"]
            })

        elif is_debit:
            remaining = row["amount"]
            destination = row["to_account"]

            while remaining > 0 and credit_queue:
                credit = credit_queue[0]
                used = min(remaining, credit["amount"])

                trail.append({
                    "debit_txn_id": row["txn_id"],
                    "debit_date": str(row["date"]),
                    "destination": destination,
                    "amount_used": used,
                    "originally_from": credit["source"],
                    "credit_date": str(credit["date"]),
                })

                credit["amount"] -= used
                remaining -= used

                if credit["amount"] == 0:
                    credit_queue.popleft()

            if remaining > 0:
                trail.append({
                    "debit_txn_id": row["txn_id"],
                    "debit_date": str(row["date"]),
                    "destination": destination,
                    "amount_used": remaining,
                    "originally_from": "PRE_EXISTING_BALANCE",
                    "credit_date": None,
                })

    return {
        "account": target_account,
        "trail": trail,
        "unspent_credits": list(credit_queue),
        "total_traced": sum(t["amount_used"] for t in trail)
    }


if __name__ == "__main__":
    from test_data import get_mock_transactions

    df = get_mock_transactions()

    # Trace where money went through HDFC mule account
    result = trace_fifo_trail(df, "HDFC_5678")

    print(f" FIFO Trail for {result['account']}:")
    print(f"   Total traced: ₹{result['total_traced']:,}\n")

    for entry in result["trail"]:
        print(f"  ₹{entry['amount_used']:,}")
        print(f"    came from  → {entry['originally_from']}")
        print(f"    went to    → {entry['destination']}")
        print(f"    on         → {entry['debit_date']}")
        print()

    if result["unspent_credits"]:
        print(" Unspent credits still sitting in account:")
        for c in result["unspent_credits"]:
            print(f"  ₹{c['amount']:,} from {c['source']}")