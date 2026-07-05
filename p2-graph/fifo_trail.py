import pandas as pd
from collections import deque


def trace_fifo_trail(df: pd.DataFrame, target_account: str) -> dict:
    account_txns = df[
        (
        (df["from_account"] == target_account)  # ALL debits including bounces
        |
        (
            (df["to_account"] == target_account) &
            (df["is_reversal"] == False)  # only non-reversal credits
        )
    )
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


def trace_all_suspicious_accounts(df: pd.DataFrame, node_flags: dict) -> dict:
    """
    Run FIFO trail on all HIGH and MEDIUM risk accounts.
    Previously only ran on HIGH — now includes MEDIUM (velocity anomaly accounts).
    """
    fifo_trails = {}
    suspicious = [
        acc for acc, info in node_flags.items()
        if info.get("risk") in ("HIGH", "MEDIUM")
    ]
    for account in suspicious:
        result = trace_fifo_trail(df, account)
        if result["trail"]:
            fifo_trails[account] = result
    return fifo_trails


if __name__ == "__main__":
    from test_data import get_mock_transactions

    df = get_mock_transactions()

    result = trace_fifo_trail(df, "HDFC_5678")

    print(f"FIFO Trail for {result['account']}:")
    print(f"  Total traced: Rs.{result['total_traced']:,}\n")

    for entry in result["trail"]:
        print(f"  Rs.{entry['amount_used']:,}")
        print(f"    came from  → {entry['originally_from']}")
        print(f"    went to    → {entry['destination']}")
        print(f"    on         → {entry['debit_date']}")
        print()

    if result["unspent_credits"]:
        print("Unspent credits still sitting in account:")
        for c in result["unspent_credits"]:
            print(f"  Rs.{c['amount']:,} from {c['source']}")

def build_money_trail(df: pd.DataFrame, target_account: str):
    """
    Returns a nested FIFO money trail.

    Each CREDIT contains the list of DEBITS that consumed it.
    """
    print(">>> USING build_money_trail <<<")
    account_txns = df[
        (
            # Include ALL debits from this account (even reversals/bounces — they consume credits)
            (df["from_account"] == target_account)
            |
            # Only include NON-reversal credits (reversal credits are money coming back, not real income)
            (
                (df["to_account"] == target_account)
                & (df["is_reversal"] == False)
            )
        )
    ].sort_values("date").copy()

    credit_queue = deque()
    money_trail = []

    for _, row in account_txns.iterrows():

        ####################################
        # CREDIT
        ####################################
        if row["to_account"] == target_account:

            credit = {
                "credit_txn_id": row["txn_id"],
                "credit_date": str(row["date"]),
                "source": row["from_account"],
                "credit_amount": float(row["amount"]),
                "remaining_amount": float(row["amount"]),
                "debits": []
            }

            credit_queue.append(credit)
            money_trail.append(credit)

        ####################################
        # DEBIT
        ####################################
        elif row["from_account"] == target_account:

            remaining = float(row["amount"])

            while remaining > 0:

                ####################################
                # No credit left
                ####################################
                if not credit_queue:

                    money_trail.append({
                        "credit_txn_id": "PRE_EXISTING_BALANCE",
                        "credit_date": None,
                        "source": "PRE_EXISTING_BALANCE",
                        "credit_amount": remaining,
                        "remaining_amount": 0,
                        "debits": [
                            {
                                "debit_txn_id": row["txn_id"],
                                "debit_date": str(row["date"]),
                                "destination": row["to_account"],
                                "amount_used": remaining,
                            }
                        ]
                    })

                    remaining = 0
                    break

                ####################################
                # FIFO allocation
                ####################################
                oldest_credit = credit_queue[0]

                used = min(
                    remaining,
                    oldest_credit["remaining_amount"]
                )

                oldest_credit["debits"].append({
                    "debit_txn_id": row["txn_id"],
                    "debit_date": str(row["date"]),
                    "destination": row["to_account"],
                    "amount_used": used,
                })

                oldest_credit["remaining_amount"] -= used
                print(
                    "UPDATED CREDIT:",
                    oldest_credit["credit_txn_id"],
                    "| credit =", oldest_credit["credit_amount"],
                    "| used =", used,
                    "| remaining =", oldest_credit["remaining_amount"]
                )
                remaining -= used

                if oldest_credit["remaining_amount"] <= 0:
                    credit_queue.popleft()
                print("\n===== FINAL MONEY TRAIL =====")

                for c in money_trail:
                    print({
                        "credit_txn_id": c["credit_txn_id"],
                        "credit_amount": c["credit_amount"],
                        "remaining_amount": c["remaining_amount"],
                        "used": sum(d["amount_used"] for d in c["debits"])
                    })

                print("=============================\n")
                print("RETURNING:")
                from pprint import pprint
                pprint(money_trail[:2])   # print first 2 credits only
    return money_trail