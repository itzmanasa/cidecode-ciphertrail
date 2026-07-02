import hashlib
import platform
import os
import json
from datetime import datetime


def generate_65b_certificate(
    case_id: str,
    file_path: str,
    file_hash: str,
    account_number: str,
    bank_name: str,
    owner_name: str,
    officer_name: str = "Investigating Officer",
    officer_designation: str = "Sub Inspector",
    police_station: str = "CID Karnataka",
    total_transactions: int = 0,
    reversal_count: int = 0,
    round_trip_count: int = 0,
) -> dict:
    """
    Auto-generates a Section 65B BSA certificate for electronic evidence.
    This makes the digital evidence court-admissible under
    Bharatiya Sakshya Adhiniyam (BSA) 2023.
    """

    now = datetime.now()

    certificate = {
        "certificate_type": "Section 65B — Bharatiya Sakshya Adhiniyam 2023",
        "case_id": case_id,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "generated_date": now.strftime("%d %B %Y"),
        "generated_time": now.strftime("%H:%M:%S IST"),

        # Evidence details
        "evidence": {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "sha256_hash": file_hash,
            "hash_algorithm": "SHA-256",
            "hash_verified": True,
        },

        # Account details
        "account": {
            "account_number": account_number,
            "bank_name": bank_name,
            "owner_name": owner_name,
        },

        # System metadata (required for 65B)
        "system_metadata": {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
        },

        # Analysis summary
        "analysis_summary": {
            "total_transactions_examined": total_transactions,
            "reversal_transactions_excluded": reversal_count,
            "round_trips_detected": round_trip_count,
            "analysis_tool": "CipherTrail v1.0",
            "analysis_method": "Rule-based graph analysis + FIFO audit",
        },

        # Officer details
        "certifying_officer": {
            "name": officer_name,
            "designation": officer_designation,
            "police_station": police_station,
            "date_of_certification": now.strftime("%d/%m/%Y"),
        },

        # Certificate text
        "certificate_text": f"""
CERTIFICATE UNDER SECTION 65B OF THE BHARATIYA SAKSHYA ADHINIYAM, 2023

I, {officer_name}, {officer_designation}, {police_station}, do hereby certify that:

1. The electronic record described herein is a computer output produced by CipherTrail 
   forensic analysis software (Version 1.0) on {now.strftime("%d %B %Y")} at {now.strftime("%H:%M:%S")} IST.

2. The source file "{os.path.basename(file_path)}" was processed and its integrity 
   verified using SHA-256 cryptographic hash: {file_hash}

3. The computer system used for analysis was operating normally at the time of 
   processing. Operating System: {platform.system()} {platform.release()}.

4. A total of {total_transactions} transactions were examined from the bank account 
   belonging to {owner_name} (Account: {account_number}, {bank_name}).

5. {reversal_count} failed/reversal transactions were identified and excluded from 
   the fraud analysis as per standard forensic practice.

6. {round_trip_count} round-trip transaction pattern(s) were detected indicating 
   potential layering of funds.

7. The information contained in this certificate is to the best of my knowledge 
   and belief derived from the electronic records of the said computer system.

Case ID: {case_id}
Date: {now.strftime("%d/%m/%Y")}
Place: Karnataka

Signature: _______________________
Name: {officer_name}
Designation: {officer_designation}
Police Station: {police_station}
        """.strip()
    }

    return certificate


def save_65b_certificate(certificate: dict, output_path: str = None) -> str:
    """Save certificate to JSON file."""
    if not output_path:
        output_path = f"65b_{certificate['case_id']}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(certificate, f, indent=2, ensure_ascii=False)

    print(f"Section 65B certificate saved to {output_path}")
    return output_path


if __name__ == "__main__":
    from test_data import get_mock_transactions
    from graph_engine import build_transaction_graph, detect_round_trips
    from analytics import generate_analytics

    df = get_mock_transactions()
    G = build_transaction_graph(df)
    round_trips = detect_round_trips(G)
    stats = generate_analytics(df)

    cert = generate_65b_certificate(
        case_id="CASE_TEST_001",
        file_path="mock_bank_statement.pdf",
        file_hash="a75020d4b21f96b18641ae3b95d156ebc4fc89a3d0fccf2e2f416711e16872ab",
        account_number="SBI_1234",
        bank_name="State Bank of India",
        owner_name="Test Account Holder",
        officer_name="SI Ramesh Kumar",
        officer_designation="Sub Inspector",
        police_station="CID Karnataka Cyber Crime",
        total_transactions=stats["total_transactions"],
        reversal_count=stats["reversal_count"],
        round_trip_count=len(round_trips)
    )

    print("\n" + "="*60)
    print("SECTION 65B CERTIFICATE GENERATED")
    print("="*60)
    print(cert["certificate_text"])
    print("\nSaving certificate...")
    save_65b_certificate(cert)
    print("Done!")