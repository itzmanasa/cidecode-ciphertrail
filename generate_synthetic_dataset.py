"""
generate_synthetic_dataset.py — Day 4 Morning
================================================
Generates a synthetic multi-account dataset for P2 and P3 to test against
BEFORE real hackathon data arrives. Contains intentional, known patterns:

  - ~2000 total transactions across 15 accounts
  - 3 distinct round-trip patterns (A→B→A, A→B→C→A, A→B→C→D→A)
  - 5 mule account hops (rapid pass-through: money in, money out within hours)
  - 1 ₹10cr victim→accused scenario (afternoon deliverable) with cash/cheque mix

Run: python generate_synthetic_dataset.py
Output: synthetic_dataset.json (BankStatement-compatible, one entry per account)
Also outputs ground_truth.json — the answer key for verifying P2's detection logic.

Usage for P2: load synthetic_dataset.json, run your graph + cycle detection,
compare your output against ground_truth.json to confirm correctness.
"""

import json
import random
import string
from datetime import datetime, timedelta

random.seed(42)  # Reproducible — same dataset every run

NUM_ACCOUNTS = 15
TOTAL_TARGET_TXNS = 2000
BASE_DATE = datetime(2025, 1, 1)

BANKS = ["HDFC Bank", "SBI", "ICICI Bank", "Axis Bank", "IDFC First Bank", "Kotak Mahindra Bank"]


def random_account_number():
    return "".join(random.choices(string.digits, k=12))


def random_name():
    first = random.choice(["Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali",
                            "Rohan", "Divya", "Karan", "Pooja", "Arjun", "Meera"])
    last = random.choice(["Sharma", "Patel", "Singh", "Reddy", "Gupta", "Nair",
                           "Iyer", "Verma", "Joshi", "Mehta"])
    return f"{first} {last}"


def fmt_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


class AccountBuilder:
    """Builds one account's transaction list incrementally with running balance."""

    def __init__(self, account_number, bank_name, owner_name, opening_balance=50000.0):
        self.account_number = account_number
        self.bank_name = bank_name
        self.owner_name = owner_name
        self.balance = opening_balance
        self.opening_balance = opening_balance
        self.transactions = []
        self.txn_counter = 0

    def add_txn(self, date, particulars, debit=0.0, credit=0.0,
                status="SUCCESS", ref_number=None):
        self.balance = round(self.balance + credit - debit, 2)
        txn = {
            "txn_id": f"{self.account_number}_{self.txn_counter:04d}",
            "date": fmt_date(date),
            "particulars": particulars,
            "debit": round(debit, 2),
            "credit": round(credit, 2),
            "balance": self.balance,
            "txn_type": "DEBIT" if debit > 0 else ("CREDIT" if credit > 0 else "UNKNOWN"),
            "status": status,
            "ref_number": ref_number or f"REF{random.randint(100000,999999)}",
            "raw_row_index": self.txn_counter,
        }
        self.transactions.append(txn)
        self.txn_counter += 1
        return txn

    def to_statement(self):
        return {
            "account_number":  self.account_number,
            "bank_name":       self.bank_name,
            "owner_name":      self.owner_name,
            "branch":          f"{random.choice(['MG Road','Koramangala','Andheri','Connaught Place'])} Branch",
            "ifsc":            f"{self.bank_name[:4].upper()}0{random.randint(100000,999999)}",
            "email":           f"{self.owner_name.lower().replace(' ','.')}@email.com",
            "period_from":     fmt_date(BASE_DATE),
            "period_to":       fmt_date(BASE_DATE + timedelta(days=180)),
            "opening_balance": self.opening_balance,
            "closing_balance": self.balance,
            "source_file":     f"synthetic_{self.account_number}.json",
            "parse_method":    "synthetic_generator",
            "transactions":    self.transactions,
            "parse_warnings":  [],
        }


def generate_dataset():
    accounts = {}
    ground_truth = {
        "round_trips": [],
        "mule_accounts": [],
        "victim_accused_scenario": {},
        "total_accounts": NUM_ACCOUNTS,
    }

    for i in range(NUM_ACCOUNTS):
        acc_no = random_account_number()
        accounts[f"ACC_{i}"] = AccountBuilder(
            acc_no, random.choice(BANKS), random_name(),
            opening_balance=random.uniform(20000, 200000)
        )

    acc_keys = list(accounts.keys())

    # ── Baseline noise transactions ───────────────────────────────────────────
    for _ in range(TOTAL_TARGET_TXNS - 200):
        acc_key = random.choice(acc_keys)
        acc = accounts[acc_key]
        current_date = BASE_DATE + timedelta(days=random.randint(0, 180))
        is_debit = random.random() > 0.5
        amount = round(random.uniform(500, 50000), 2)

        narration_pool = [
            f"UPI/{random.randint(100000000000,999999999999)}/Payment",
            f"NEFT/Transfer to {random_name()}",
            "ATM CASH WITHDRAWAL",
            f"CHEQUE PAYMENT CHQ NO {random.randint(100000,999999)}",
            f"IMPS/{random.randint(100000000000,999999999999)}/Transfer",
            "Salary credit",
            "Online shopping payment",
        ]
        narration = random.choice(narration_pool)

        if is_debit:
            acc.add_txn(current_date, narration, debit=amount)
        else:
            acc.add_txn(current_date, narration, credit=amount)

    # ── PATTERN 1: Simple round-trip A → B → A ────────────────────────────────
    a, b = accounts[acc_keys[0]], accounts[acc_keys[1]]
    amount = 250000.0
    d1 = BASE_DATE + timedelta(days=30)
    d2 = d1 + timedelta(days=2)

    a.add_txn(d1, f"NEFT to {b.owner_name}/ACC{b.account_number}", debit=amount)
    b.add_txn(d1, f"NEFT from {a.owner_name}/ACC{a.account_number}", credit=amount)
    b.add_txn(d2, f"NEFT to {a.owner_name}/ACC{a.account_number}", debit=amount)
    a.add_txn(d2, f"NEFT from {b.owner_name}/ACC{a.account_number}", credit=amount)

    ground_truth["round_trips"].append({
        "pattern": "A_B_A",
        "accounts": [a.account_number, b.account_number],
        "amount": amount,
        "hops": 2,
        "start_date": fmt_date(d1),
        "end_date": fmt_date(d2),
        "days_elapsed": (d2 - d1).days,
    })

    # ── PATTERN 2: Three-hop round-trip A → B → C → A ─────────────────────────
    a, b, c = accounts[acc_keys[2]], accounts[acc_keys[3]], accounts[acc_keys[4]]
    amount = 500000.0
    d1 = BASE_DATE + timedelta(days=60)
    d2 = d1 + timedelta(hours=18)
    d3 = d1 + timedelta(days=1, hours=6)

    a.add_txn(d1, f"RTGS to {b.owner_name}/ACC{b.account_number}", debit=amount)
    b.add_txn(d1, f"RTGS from {a.owner_name}/ACC{a.account_number}", credit=amount)
    b.add_txn(d2, f"RTGS to {c.owner_name}/ACC{c.account_number}", debit=amount)
    c.add_txn(d2, f"RTGS from {b.owner_name}/ACC{b.account_number}", credit=amount)
    c.add_txn(d3, f"RTGS to {a.owner_name}/ACC{a.account_number}", debit=amount)
    a.add_txn(d3, f"RTGS from {c.owner_name}/ACC{c.account_number}", credit=amount)

    ground_truth["round_trips"].append({
        "pattern": "A_B_C_A",
        "accounts": [a.account_number, b.account_number, c.account_number],
        "amount": amount,
        "hops": 3,
        "start_date": fmt_date(d1),
        "end_date": fmt_date(d3),
        "days_elapsed": (d3 - d1).days,
    })

    # ── PATTERN 3: Four-hop round-trip A → B → C → D → A ──────────────────────
    a, b, c, d = (accounts[acc_keys[5]], accounts[acc_keys[6]],
                  accounts[acc_keys[7]], accounts[acc_keys[8]])
    amount = 1000000.0
    t1 = BASE_DATE + timedelta(days=90)
    t2 = t1 + timedelta(hours=4)
    t3 = t1 + timedelta(hours=9)
    t4 = t1 + timedelta(hours=15)

    a.add_txn(t1, f"IMPS to {b.owner_name}/ACC{b.account_number}", debit=amount)
    b.add_txn(t1, f"IMPS from {a.owner_name}/ACC{a.account_number}", credit=amount)
    b.add_txn(t2, f"IMPS to {c.owner_name}/ACC{c.account_number}", debit=amount)
    c.add_txn(t2, f"IMPS from {b.owner_name}/ACC{b.account_number}", credit=amount)
    c.add_txn(t3, f"IMPS to {d.owner_name}/ACC{d.account_number}", debit=amount)
    d.add_txn(t3, f"IMPS from {c.owner_name}/ACC{c.account_number}", credit=amount)
    d.add_txn(t4, f"IMPS to {a.owner_name}/ACC{a.account_number}", debit=amount)
    a.add_txn(t4, f"IMPS from {d.owner_name}/ACC{a.account_number}", credit=amount)

    ground_truth["round_trips"].append({
        "pattern": "A_B_C_D_A",
        "accounts": [a.account_number, b.account_number, c.account_number, d.account_number],
        "amount": amount,
        "hops": 4,
        "start_date": fmt_date(t1),
        "end_date": fmt_date(t4),
        "hours_elapsed": (t4 - t1).total_seconds() / 3600,
    })

    # ── MULE HOPS: 5 accounts that receive then immediately forward ──────────
    mule_source_idx = [9, 10, 11, 12, 13]
    for idx in mule_source_idx:
        mule = accounts[acc_keys[idx]]
        destination = accounts[random.choice([k for k in acc_keys if k != acc_keys[idx]])]
        amount = round(random.uniform(80000, 400000), 2)
        in_time  = BASE_DATE + timedelta(days=random.randint(100, 150), hours=random.randint(0, 23))
        out_time = in_time + timedelta(hours=random.uniform(0.5, 4))

        mule.add_txn(in_time, f"IMPS IN/{random.randint(100000000000,999999999999)}/Mule inflow", credit=amount)
        mule.add_txn(out_time, f"IMPS OUT/{random.randint(100000000000,999999999999)}/Forwarded to {destination.owner_name}", debit=amount)
        destination.add_txn(out_time, f"IMPS from {mule.owner_name}/ACC{mule.account_number}", credit=amount)

        ground_truth["mule_accounts"].append({
            "account_number":   mule.account_number,
            "owner_name":       mule.owner_name,
            "inflow_time":      in_time.isoformat(),
            "outflow_time":     out_time.isoformat(),
            "hold_duration_hours": round((out_time - in_time).total_seconds() / 3600, 2),
            "amount":           amount,
            "destination_account": destination.account_number,
        })

    # ── ₹10cr victim → accused scenario with cash/cheque breakdown ───────────
    victim   = accounts["ACC_14"]
    accused  = AccountBuilder(random_account_number(), "HDFC Bank", "Suspicious Person",
                               opening_balance=10000.0)
    accounts["ACC_ACCUSED"] = accused

    total_amount = 100_000_000.0  # ₹10 crore
    d_start = BASE_DATE + timedelta(days=120)

    victim.add_txn(d_start, f"RTGS to {accused.owner_name}/ACC{accused.account_number}", debit=total_amount)
    accused.add_txn(d_start, f"RTGS from {victim.owner_name}/ACC{victim.account_number}", credit=total_amount)

    cash_total = 0.0
    cheque_total = 0.0
    remaining = total_amount
    breakdown = []

    for _ in range(8):
        if remaining <= 0:
            break
        is_cash = random.random() > 0.5
        chunk = round(min(remaining, random.uniform(5_000_000, 20_000_000)), 2)
        chunk_date = d_start + timedelta(days=random.randint(1, 10))

        if is_cash:
            accused.add_txn(chunk_date, "ATM CASH WITHDRAWAL", debit=chunk)
            cash_total += chunk
            breakdown.append({"type": "CASH", "amount": chunk, "date": fmt_date(chunk_date)})
        else:
            chq_no = random.randint(100000, 999999)
            accused.add_txn(chunk_date, f"CHEQUE PAYMENT CHQ NO {chq_no}", debit=chunk)
            cheque_total += chunk
            breakdown.append({"type": "CHEQUE", "amount": chunk, "date": fmt_date(chunk_date), "cheque_no": chq_no})

        remaining -= chunk

    ground_truth["victim_accused_scenario"] = {
        "victim_account":    victim.account_number,
        "victim_name":       victim.owner_name,
        "accused_account":   accused.account_number,
        "accused_name":      accused.owner_name,
        "total_amount":      total_amount,
        "transfer_date":     fmt_date(d_start),
        "cash_withdrawal_total":   round(cash_total, 2),
        "cheque_withdrawal_total": round(cheque_total, 2),
        "remaining_in_account":    round(remaining, 2),
        "breakdown": breakdown,
    }

    all_statements = [acc.to_statement() for acc in accounts.values()]
    total_txns = sum(len(s["transactions"]) for s in all_statements)
    ground_truth["actual_total_transactions"] = total_txns
    ground_truth["actual_account_count"] = len(all_statements)

    return all_statements, ground_truth


if __name__ == "__main__":
    print("Generating synthetic dataset...")
    statements, ground_truth = generate_dataset()

    with open("synthetic_dataset.json", "w") as f:
        json.dump(statements, f, indent=2)

    with open("ground_truth.json", "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"✅ Generated {ground_truth['actual_total_transactions']} transactions "
          f"across {ground_truth['actual_account_count']} accounts")
    print(f"✅ Round-trip patterns embedded: {len(ground_truth['round_trips'])}")
    print(f"✅ Mule account hops embedded: {len(ground_truth['mule_accounts'])}")
    print(f"✅ Victim→Accused scenario: ₹{ground_truth['victim_accused_scenario']['total_amount']:,.0f}")
    print(f"   Cash: ₹{ground_truth['victim_accused_scenario']['cash_withdrawal_total']:,.0f}")
    print(f"   Cheque: ₹{ground_truth['victim_accused_scenario']['cheque_withdrawal_total']:,.0f}")
    print("\nFiles written: synthetic_dataset.json, ground_truth.json")
    print("Hand both files to P2 (graph detection) and P3 (frontend testing).")
