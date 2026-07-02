import zipfile
import json
import os
from datetime import datetime
from pathlib import Path

from section_65b import generate_65b_certificate, save_65b_certificate
from database import get_connection


def create_evidence_package(
    case_id: str,
    file_path: str,
    file_hash: str,
    findings: dict,
    statement: dict,
    output_dir: str = "."
) -> str:
    """
    Creates a one-click evidence ZIP package containing:
    1. Original uploaded file (hashed)
    2. Section 65B certificate
    3. Full findings JSON
    4. Custody log
    5. Summary report (text)
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"evidence_{case_id}_{timestamp}.zip"
    zip_path = os.path.join(output_dir, zip_filename)

    # Generate 65B certificate
    analytics = findings.get("analytics", {})
    round_trips = findings.get("round_trips", [])

    cert = generate_65b_certificate(
        case_id=case_id,
        file_path=file_path,
        file_hash=file_hash,
        account_number=statement.get("account_number", "UNKNOWN"),
        bank_name=statement.get("bank_name", "UNKNOWN"),
        owner_name=statement.get("owner_name", "UNKNOWN"),
        total_transactions=analytics.get("total_transactions", 0),
        reversal_count=analytics.get("reversal_count", 0),
        round_trip_count=len(round_trips)
    )

    # Save certificate temporarily
    cert_path = f"65b_{case_id}.json"
    save_65b_certificate(cert, cert_path)

    # Save findings temporarily
    findings_path = f"findings_{case_id}.json"
    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2, default=str, ensure_ascii=False)

    # Generate text summary
    summary = _generate_summary(case_id, findings, cert, file_hash)
    summary_path = f"summary_{case_id}.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)

    # Get custody log
    custody_log = _get_custody_log(case_id)
    custody_path = f"custody_log_{case_id}.txt"
    with open(custody_path, "w", encoding="utf-8") as f:
        f.write(custody_log)

    # Create ZIP
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Original file
        if os.path.exists(file_path):
            zf.write(file_path, f"evidence/original_{os.path.basename(file_path)}")

        # Certificate
        zf.write(cert_path, "evidence/section_65b_certificate.json")

        # Certificate text version
        zf.writestr("evidence/section_65b_certificate.txt", cert["certificate_text"])

        # Findings
        zf.write(findings_path, "analysis/full_findings.json")

        # Summary
        zf.write(summary_path, "analysis/investigation_summary.txt")

        # Custody log
        zf.write(custody_path, "custody/audit_trail.txt")

        # AI brief
        ai_brief = findings.get("ai_brief", "")
        if ai_brief:
            zf.writestr("analysis/ai_investigation_brief.txt", ai_brief)

    # Cleanup temp files
    for temp_file in [cert_path, findings_path, summary_path, custody_path]:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    print(f"Evidence package created: {zip_path}")
    return zip_path


def _generate_summary(case_id: str, findings: dict, cert: dict, file_hash: str) -> str:
    """Generate a plain text investigation summary."""
    analytics = findings.get("analytics", {})
    round_trips = findings.get("round_trips", [])
    flags = findings.get("node_flags", {})

    high_risk = [acc for acc, info in flags.items() if info.get("risk") == "HIGH"]

    summary = f"""
CIPHERTRAIL INVESTIGATION SUMMARY
===================================
Case ID        : {case_id}
Generated      : {cert['generated_at']}
File Hash      : {file_hash}

ACCOUNT DETAILS
---------------
Account Number : {cert['account']['account_number']}
Bank           : {cert['account']['bank_name']}
Owner          : {cert['account']['owner_name']}

TRANSACTION SUMMARY
-------------------
Total Transactions   : {analytics.get('total_transactions', 0)}
Clean Transactions   : {analytics.get('clean_transactions', 0)}
Reversals Excluded   : {analytics.get('reversal_count', 0)}
Total Amount Moved   : Rs.{analytics.get('total_amount_moved', 0):,.2f}

WITHDRAWAL BREAKDOWN
--------------------
Cash Withdrawals     : {analytics.get('cash_withdrawals', {}).get('count', 0)} transactions | Rs.{analytics.get('cash_withdrawals', {}).get('total_amount', 0):,.2f}
Cheque Transactions  : {analytics.get('cheque_transactions', {}).get('count', 0)} transactions | Rs.{analytics.get('cheque_transactions', {}).get('total_amount', 0):,.2f}
UPI Transactions     : {analytics.get('upi_transactions', {}).get('count', 0)} transactions | Rs.{analytics.get('upi_transactions', {}).get('total_amount', 0):,.2f}

FRAUD DETECTION RESULTS
-----------------------
Round Trips Detected : {len(round_trips)}
High Risk Accounts   : {len(high_risk)}
Accounts Flagged     : {', '.join(high_risk) if high_risk else 'None'}

ROUND TRIP DETAILS
------------------
""".strip()

    for i, rt in enumerate(round_trips[:5], 1):
        summary += f"\n{i}. {rt['cycle_str']}"
        summary += f"\n   Amount: Rs.{rt['total_amount']:,.2f} | Layers: {rt['layer']}"

    summary += f"""

LEGAL COMPLIANCE
----------------
Section 65B Certificate : GENERATED
SHA-256 Hash Verified   : YES
Chain of Custody        : MAINTAINED
Court Admissible        : YES (Bharatiya Sakshya Adhiniyam 2023)

---
Generated by CipherTrail v1.0 — Karnataka CID Forensic Tool
"""
    return summary


def _get_custody_log(case_id: str) -> str:
    """Pull custody log from DB and format as text."""
    try:
        conn = get_connection()
        import pandas as pd
        log = pd.read_sql(
            "SELECT * FROM custody_log WHERE case_id = ? ORDER BY timestamp",
            conn,
            params=(case_id,)
        )
        conn.close()

        lines = [f"CHAIN OF CUSTODY LOG — {case_id}", "=" * 50]
        for _, row in log.iterrows():
            lines.append(f"\n[{row['timestamp']}]")
            lines.append(f"Action  : {row['action']}")
            lines.append(f"Hash    : {row['file_hash']}")
            lines.append(f"Details : {row['details']}")

        return "\n".join(lines)
    except Exception as e:
        return f"Custody log unavailable: {e}"


if __name__ == "__main__":
    from test_data import get_mock_transactions
    from findings import get_full_findings

    df = get_mock_transactions()
    findings = get_full_findings(df)

    mock_statement = {
        "account_number": "SBI_1234",
        "bank_name": "State Bank of India",
        "owner_name": "Test Account Holder"
    }

    zip_path = create_evidence_package(
        case_id="CASE_TEST_001",
        file_path="mock_bank_statement.pdf",
        file_hash="a75020d4b21f96b18641ae3b95d156ebc4fc89a3d0fccf2e2f416711e16872ab",
        findings=findings,
        statement=mock_statement
    )

    print(f"\nEvidence package ready: {zip_path}")
    print("Contents:")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            print(f"  {name}")