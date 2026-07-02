import pandas as pd


def generate_analytics(df: pd.DataFrame) -> dict:
    clean = df[df["is_reversal"] == False].copy()
    reversals = df[df["is_reversal"] == True].copy()

    def classify(narration: str) -> str:
        n = str(narration).upper()
        if "ATM" in n or "CASH" in n:
            return "CASH"
        elif "CHEQUE" in n or "CHQ" in n or "CTS" in n:
            return "CHEQUE"
        elif "UPI" in n:
            return "UPI"
        elif "NEFT" in n:
            return "NEFT"
        elif "RTGS" in n:
            return "RTGS"
        elif "IMPS" in n:
            return "IMPS"
        else:
            return "OTHER"

    clean["txn_type"] = clean["narration"].apply(classify)

    cash  = clean[clean["txn_type"] == "CASH"]
    cheque = clean[clean["txn_type"] == "CHEQUE"]
    upi   = clean[clean["txn_type"] == "UPI"]

    sent = clean.groupby("from_account")["amount"].sum().reset_index()
    sent.columns = ["account", "total_sent"]

    received = clean.groupby("to_account")["amount"].sum().reset_index()
    received.columns = ["account", "total_received"]

    top_accounts = pd.merge(sent, received, on="account", how="outer").fillna(0)
    top_accounts["total_flow"] = top_accounts["total_sent"] + top_accounts["total_received"]
    top_accounts = top_accounts.sort_values("total_flow", ascending=False)

    return {
        "total_transactions": len(df),
        "clean_transactions": len(clean),
        "reversal_count": len(reversals),
        "reversal_amount": float(reversals["amount"].sum()) if len(reversals) else 0,
        "total_amount_moved": float(clean["amount"].sum()),

        "cash_withdrawals": {
            "count": int(len(cash)),
            "total_amount": float(cash["amount"].sum())
        },
        "cheque_transactions": {
            "count": int(len(cheque)),
            "total_amount": float(cheque["amount"].sum())
        },
        "upi_transactions": {
            "count": int(len(upi)),
            "total_amount": float(upi["amount"].sum())
        },

        "transaction_type_breakdown": clean["txn_type"].value_counts().to_dict(),
        "top_accounts": top_accounts.head(10).to_dict(orient="records")
    }


if __name__ == "__main__":
    from test_data import get_mock_transactions

    df = get_mock_transactions()
    stats = generate_analytics(df)

    print("📊 Analytics Summary")
    print(f"  Total transactions : {stats['total_transactions']}")
    print(f"  Clean transactions : {stats['clean_transactions']}")
    print(f"  Reversals detected : {stats['reversal_count']} (₹{stats['reversal_amount']:,})")
    print(f"  Total amount moved : ₹{stats['total_amount_moved']:,}")
    print(f"\n  Cash withdrawals   : {stats['cash_withdrawals']['count']} txns | ₹{stats['cash_withdrawals']['total_amount']:,}")
    print(f"  Cheque txns        : {stats['cheque_transactions']['count']} txns | ₹{stats['cheque_transactions']['total_amount']:,}")
    print(f"  UPI txns           : {stats['upi_transactions']['count']} txns | ₹{stats['upi_transactions']['total_amount']:,}")
    print(f"\n  Type breakdown     : {stats['transaction_type_breakdown']}")
    print(f"\n  Top accounts by flow:")
    for acc in stats["top_accounts"]:
        print(f"    {acc['account']:15} | sent ₹{acc['total_sent']:>12,.0f} | received ₹{acc['total_received']:>12,.0f} | flow ₹{acc['total_flow']:>12,.0f}")