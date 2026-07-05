import pandas as pd
import re


def extract_counterparty(particulars: str, txn_type: str) -> str:
    """
    Try to extract the other account from the narration.
    Falls back to narration-based label if not found.
    """
    p = str(particulars).upper()

    # UPI pattern: extract UPI ID or phone number
    upi_match = re.search(r"UPI[/-]([A-Z0-9@._]+)", p)
    if upi_match:
        return f"UPI_{upi_match.group(1)[:20]}"

    # NEFT/RTGS/IMPS with account reference
    neft_match = re.search(r"(NEFT|RTGS|IMPS)[/-]?([A-Z0-9]+)", p)
    if neft_match:
        return f"{neft_match.group(1)}_{neft_match.group(2)[:15]}"

    # ATM withdrawal
    if "ATM" in p:
        location = re.search(r"ATM[/\-\s]+([A-Z\s]+?)(?:\s+\d|\s*$)", p)
        if location:
            return f"ATM_{location.group(1).strip().replace(' ', '_')[:15]}"
        return "ATM_WITHDRAWAL"

    # Cheque
    # Cheque bounce/return — treat as a separate counterparty from normal cheque
    if ("CHQ" in p or "CHEQUE" in p) and ("BOUNCE" in p or "RETURN" in p or "DISHONOUR" in p):
        chq_match = re.search(r"CHQ\s*(?:DEPOSIT\s*BOUNCE|BOUNCE)[/\s]+(\d+)", p)
        ref = chq_match.group(1) if chq_match else "UNKNOWN"
        return f"CHQ_BOUNCE_{ref}"

    if "CHQ" in p or "CHEQUE" in p:
        chq_match = re.search(r"(?:CHQ|CHEQUE)[/\s]+(\d+)", p)
        ref = chq_match.group(1) if chq_match else "UNKNOWN"
        return f"CHEQUE_{ref}"

    # Cash
    if "CASH" in p:
        return "CASH_WITHDRAWAL"

    # Generic fallback — use first 20 chars of particulars
    clean = re.sub(r"[^A-Z0-9]", "_", p[:20]).strip("_")
    return f"EXT_{clean}" if clean else "EXTERNAL"


def adapt_statement_to_engine(statement: dict, case_id: str = None) -> pd.DataFrame:
    """
    Converts Person 1's BankStatement dict → DataFrame your engine expects.

    Your engine needs:
    txn_id, date, from_account, to_account, amount, narration, is_reversal
    """
    account_id = statement.get("account_number", "UNKNOWN")
    bank_name = statement.get("bank_name", "BANK")

    # Create a clean account label
    account_label = account_id if account_id != "UNKNOWN" else "ACCOUNT_UNKNOWN"

    rows = []
    for txn in statement.get("transactions", []):
        status = txn.get("status", "SUCCESS")
        txn_type = txn.get("txn_type", "UNKNOWN")
        particulars = txn.get("particulars", "")
        debit = float(txn.get("debit", 0) or 0)
        credit = float(txn.get("credit", 0) or 0)

        # is_reversal = True if status is REVERSAL or FAILED
        is_reversal = status in ("REVERSAL", "FAILED")

        # Amount = whichever is non-zero
        amount = debit if debit > 0 else credit

        # from/to account based on direction
        counterparty = extract_counterparty(particulars, txn_type)

        if txn_type == "DEBIT":
            from_account = account_label
            to_account = counterparty
        elif txn_type == "CREDIT":
            from_account = counterparty
            to_account = account_label
        else:
            from_account = account_label
            to_account = "UNKNOWN"

        rows.append({
            "txn_id": txn.get("txn_id", ""),
            "date": pd.to_datetime(txn.get("date"), errors="coerce"),
            "from_account": from_account,
            "to_account": to_account,
            "amount": amount,
            "narration": particulars,
            "is_reversal": is_reversal,
            # Keep extra fields for analytics
            "debit": debit,
            "credit": credit,
            "balance": txn.get("balance", 0),
            "txn_type": txn_type,
            "status": status,
            "ref_number": txn.get("ref_number"),
            "account_id": account_label,
            "bank_name": bank_name,
            "owner_name": statement.get("owner_name", ""),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    return df


def adapt_multiple_statements(statements: list) -> pd.DataFrame:
    """
    Merge multiple bank statements into one unified DataFrame.
    Used when investigator uploads 3-5 bank PDFs at once.
    """
    all_dfs = []
    for statement in statements:
        df = adapt_statement_to_engine(statement)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    merged = pd.concat(all_dfs, ignore_index=True)
    merged = merged.sort_values("date").reset_index(drop=True)

    print(f"Merged {len(statements)} statements → {len(merged)} total transactions")
    return merged


if __name__ == "__main__":
    # Test with mock statement matching Person 1's output format
    mock_statement = {
        "account_number": "1234567890",
        "bank_name": "HDFC Bank",
        "owner_name": "Test User",
        "transactions": [
            {
                "txn_id": "1234567890_0001",
                "date": "2024-06-01",
                "particulars": "UPI/PhonePe/9876543210/payment",
                "debit": 50000.0,
                "credit": 0.0,
                "balance": 150000.0,
                "txn_type": "DEBIT",
                "status": "SUCCESS",
                "ref_number": None,
            },
            {
                "txn_id": "1234567890_0002",
                "date": "2024-06-01",
                "particulars": "NEFT/HDFC0001234/credited",
                "debit": 0.0,
                "credit": 100000.0,
                "balance": 250000.0,
                "txn_type": "CREDIT",
                "status": "SUCCESS",
                "ref_number": None,
            },
            {
                "txn_id": "1234567890_0003",
                "date": "2024-06-02",
                "particulars": "NEFT reversal failed transaction",
                "debit": 10000.0,
                "credit": 0.0,
                "balance": 240000.0,
                "txn_type": "DEBIT",
                "status": "REVERSAL",
                "ref_number": None,
            },
        ]
    }

    df = adapt_statement_to_engine(mock_statement)
    print("Adapted DataFrame:")
    print(df[["txn_id", "from_account", "to_account",
              "amount", "is_reversal", "narration"]].to_string())

    print(f"\nReversals: {df['is_reversal'].sum()}")
    print(f"Clean txns: {(~df['is_reversal']).sum()}")