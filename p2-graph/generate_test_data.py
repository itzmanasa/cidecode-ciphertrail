import pandas as pd
import random
import hashlib
from datetime import datetime, timedelta

def generate_large_dataset(num_transactions=2000, seed=42):
    random.seed(seed)

    accounts = [
        "SBI_1001", "SBI_1002", "SBI_1003",
        "HDFC_2001", "HDFC_2002", "HDFC_2003",
        "AXIS_3001", "AXIS_3002",
        "ICICI_4001", "ICICI_4002",
        "PAYTM_5001", "PAYTM_5002",
        "ATM_HUBLI", "ATM_MANGALURU", "ATM_BENGALURU"
    ]

    mule_chain_1 = ["SBI_1001", "HDFC_2001", "AXIS_3001", "SBI_1001"]
    mule_chain_2 = ["ICICI_4001", "PAYTM_5001", "HDFC_2002", "ICICI_4001"]
    mule_chain_3 = ["SBI_1002", "AXIS_3002", "ICICI_4002", "PAYTM_5002", "SBI_1002"]

    base = datetime(2024, 6, 1, 9, 0, 0)
    txns = []
    txn_counter = 1

    def make_txn(from_acc, to_acc, amount, narration, is_reversal=False, time_offset_mins=0):
        nonlocal txn_counter
        txn = {
            "txn_id": f"T{txn_counter:05d}",
            "date": base + timedelta(minutes=time_offset_mins),
            "from_account": from_acc,
            "to_account": to_acc,
            "amount": amount,
            "narration": narration,
            "is_reversal": is_reversal
        }
        txn_counter += 1
        return txn

    # Round trip chain 1 — Rs.50 lakhs
    offset = 0
    txns.append(make_txn("SBI_1001", "HDFC_2001", 5000000, "UPI/transfer/fraud", time_offset_mins=offset))
    offset += 6
    txns.append(make_txn("HDFC_2001", "AXIS_3001", 4800000, "NEFT/layering", time_offset_mins=offset))
    offset += 5
    txns.append(make_txn("AXIS_3001", "SBI_1001", 4600000, "UPI/refund", time_offset_mins=offset))
    offset += 3
    txns.append(make_txn("AXIS_3001", "ATM_HUBLI", 200000, "ATM withdrawal", time_offset_mins=offset))

    # Round trip chain 2 — Rs.30 lakhs
    offset += 10
    txns.append(make_txn("ICICI_4001", "PAYTM_5001", 3000000, "UPI/transfer", time_offset_mins=offset))
    offset += 4
    txns.append(make_txn("PAYTM_5001", "HDFC_2002", 2900000, "IMPS/transfer", time_offset_mins=offset))
    offset += 6
    txns.append(make_txn("HDFC_2002", "ICICI_4001", 2800000, "NEFT/return", time_offset_mins=offset))
    offset += 2
    txns.append(make_txn("HDFC_2002", "ATM_MANGALURU", 100000, "ATM withdrawal", time_offset_mins=offset))

    # Round trip chain 3 — Rs.20 lakhs (4 hops)
    offset += 15
    txns.append(make_txn("SBI_1002", "AXIS_3002", 2000000, "UPI/transfer", time_offset_mins=offset))
    offset += 3
    txns.append(make_txn("AXIS_3002", "ICICI_4002", 1900000, "NEFT/transfer", time_offset_mins=offset))
    offset += 4
    txns.append(make_txn("ICICI_4002", "PAYTM_5002", 1800000, "IMPS/transfer", time_offset_mins=offset))
    offset += 5
    txns.append(make_txn("PAYTM_5002", "SBI_1002", 1700000, "UPI/refund", time_offset_mins=offset))
    offset += 2
    txns.append(make_txn("PAYTM_5002", "ATM_BENGALURU", 100000, "ATM withdrawal", time_offset_mins=offset))

    # Reversals — must be excluded
    for i in range(50):
        from_acc = random.choice(accounts[:10])
        to_acc = random.choice(accounts[:10])
        amount = random.randint(1000, 50000)
        offset += random.randint(1, 5)
        txns.append(make_txn(from_acc, to_acc, amount, "failed transfer", is_reversal=True, time_offset_mins=offset))

    # Normal transactions — bulk filler
    narrations = [
        "UPI/PhonePe", "NEFT transfer", "IMPS payment",
        "ATM withdrawal", "RTGS transfer", "Cheque deposit",
        "UPI/GooglePay", "Online transfer", "NACH debit"
    ]

    for i in range(num_transactions - txn_counter + 1):
        from_acc = random.choice(accounts[:10])
        to_acc = random.choice(accounts)
        while to_acc == from_acc:
            to_acc = random.choice(accounts)
        amount = random.randint(500, 500000)
        narration = random.choice(narrations)
        is_reversal = random.random() < 0.03  # 3% reversal rate
        offset += random.randint(1, 30)
        txns.append(make_txn(from_acc, to_acc, amount, narration,
                             is_reversal=is_reversal, time_offset_mins=offset))

    df = pd.DataFrame(txns)
    print(f"Generated {len(df)} transactions")
    print(f"Reversals: {len(df[df['is_reversal']==True])}")
    print(f"Clean transactions: {len(df[df['is_reversal']==False])}")
    print(f"Accounts involved: {len(set(df['from_account'].tolist() + df['to_account'].tolist()))}")
    return df


if __name__ == "__main__":
    import time

    print("Generating 2000 transaction dataset...")
    start = time.time()
    df = generate_large_dataset(2000)
    print(f"Generated in {time.time() - start:.2f}s")

    print("\nRunning full engine on 2000 transactions...")
    start = time.time()

    from graph_engine import build_transaction_graph, detect_round_trips, flag_suspicious_nodes
    from analytics import generate_analytics

    G = build_transaction_graph(df)
    round_trips = detect_round_trips(G)
    flags = flag_suspicious_nodes(G, round_trips)
    stats = generate_analytics(df)

    elapsed = time.time() - start
    print(f"Engine completed in {elapsed:.2f}s")
    print(f"\nRound trips found: {len(round_trips)}")
    for rt in round_trips:
        print(f"  {rt['cycle_str']}")
        print(f"  Amount: Rs.{rt['total_amount']:,} | Layers: {rt['layer']}")
    print(f"\nHigh risk accounts: {[a for a,i in flags.items() if i['risk']=='HIGH']}")
    print(f"Total amount moved: Rs.{stats['total_amount_moved']:,.0f}")
    print(f"Reversals excluded: {stats['reversal_count']}")