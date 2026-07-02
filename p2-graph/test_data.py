import pandas as pd
from datetime import datetime, timedelta

def get_mock_transactions():
    base = datetime(2024, 6, 1, 10, 0, 0)

    txns = [
        # Victim sends money to Mule 1
        {"txn_id": "T001", "date": base,
         "from_account": "SBI_1234", "to_account": "HDFC_5678",
         "amount": 1420000, "narration": "UPI/transfer", "is_reversal": False},

        # Mule 1 sends to Mule 2
        {"txn_id": "T002", "date": base + timedelta(minutes=8),
         "from_account": "HDFC_5678", "to_account": "AXIS_9012",
         "amount": 720000, "narration": "NEFT transfer", "is_reversal": False},

        # Mule 2 sends back to victim account (round trip!)
        {"txn_id": "T003", "date": base + timedelta(minutes=15),
         "from_account": "AXIS_9012", "to_account": "SBI_1234",
         "amount": 700000, "narration": "UPI refund", "is_reversal": False},

        # A reversal — must be EXCLUDED from graph
        {"txn_id": "T004", "date": base + timedelta(minutes=20),
         "from_account": "HDFC_5678", "to_account": "PAYTM_3456",
         "amount": 50000, "narration": "failed transfer", "is_reversal": True},

        # Cash withdrawal — end of trail
        {"txn_id": "T005", "date": base + timedelta(minutes=23),
         "from_account": "AXIS_9012", "to_account": "ATM_HUBLI",
         "amount": 200000, "narration": "ATM withdrawal", "is_reversal": False},
    ]
    return pd.DataFrame(txns)

if __name__ == "__main__":
    df = get_mock_transactions()
    print(df)
    print(f"\nTotal transactions: {len(df)}")
    print(f"Reversals: {len(df[df['is_reversal']==True])}")
    print(f"Clean transactions: {len(df[df['is_reversal']==False])}")