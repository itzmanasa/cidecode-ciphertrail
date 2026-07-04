import pandas as pd
from collections import deque


def build_money_trail(df: pd.DataFrame, target_account: str):
    """
    Build a FIFO money trail.

    Returns a list where each CREDIT contains all the DEBITS
    that consumed that credit.

    Example:

    [
        {
            credit_txn_id: "...",
            credit_date: "...",
            source: "...",
            credit_amount: 50000,
            remaining_amount: 0,
            debits:[
                {...},
                {...}
            ]
        }
    ]
    """

    # Keep only transactions for this account
    account_txns = df[
        (df["is_reversal"] == False)
        &
        (
            (df["from_account"] == target_account)
            |
            (df["to_account"] == target_account)
        )
    ].sort_values("date").copy()

    credit_queue = deque()
    money_trail = []

    for _, row in account_txns.iterrows():

        ####################################
        # CREDIT INTO ACCOUNT
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
        # DEBIT FROM ACCOUNT
        ####################################
        elif row["from_account"] == target_account:

            remaining = float(row["amount"])

            while remaining > 0:

                ####################################
                # No credits left
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
                                "amount_used": remaining
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
                    "amount_used": used
                })

                oldest_credit["remaining_amount"] -= used
                remaining -= used

                if oldest_credit["remaining_amount"] <= 0:
                    credit_queue.popleft()

    return money_trail


if __name__ == "__main__":

    from test_data import get_mock_transactions

    df = get_mock_transactions()

    target = "HDFC_5678"

    trail = build_money_trail(df, target)

    from pprint import pprint

    pprint(trail)