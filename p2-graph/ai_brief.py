import json
import os
import sys
from dotenv import load_dotenv
from groq import Groq

sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CACHED_RESPONSE = None


def generate_investigation_brief(findings: dict) -> str:
    global CACHED_RESPONSE

    prompt = f"""You are a forensic report writer for Karnataka CID.
Based ONLY on the confirmed findings below, write a 3-paragraph
investigation brief in formal police report style.
Do NOT add any information not present in the data below.

CONFIRMED FINDINGS:
{json.dumps(findings, indent=2)}

Write exactly 3 paragraphs:
Paragraph 1: Summary of accounts involved, total amount, and time period
Paragraph 2: Description of the round-trip pattern with full account chain
Paragraph 3: Recommended immediate actions (freeze orders, warrants, etc.)

Be specific with amounts and account IDs. Use formal language.
Use Rs. instead of rupee symbol."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )

        brief = response.choices[0].message.content
        CACHED_RESPONSE = brief

        with open("cached_brief.txt", "w", encoding="utf-8") as f:
            f.write(brief)

        return brief

    except Exception as e:
        print(f"Groq API error: {e}")

        if os.path.exists("cached_brief.txt"):
            print("Using cached brief from file")
            with open("cached_brief.txt", "r", encoding="utf-8") as f:
                return f.read()

        if CACHED_RESPONSE:
            return CACHED_RESPONSE

        return "AI brief unavailable. Please refer to the rule-based findings above."


if __name__ == "__main__":
    from test_data import get_mock_transactions
    from graph_engine import build_transaction_graph, detect_round_trips, flag_suspicious_nodes
    from analytics import generate_analytics

    df = get_mock_transactions()
    G = build_transaction_graph(df)
    round_trips = detect_round_trips(G)
    flags = flag_suspicious_nodes(G, round_trips)
    stats = generate_analytics(df)

    findings = {
        "case_summary": {
            "total_accounts": G.number_of_nodes(),
            "total_transactions": stats["clean_transactions"],
            "reversals_excluded": stats["reversal_count"],
            "total_amount_moved": stats["total_amount_moved"],
        },
        "round_trips": [
            {
                "chain": rt["cycle_str"],
                "total_amount": rt["total_amount"],
                "layers": rt["layer"],
                "hops": rt["hops"]
            }
            for rt in round_trips[:3]
        ],
        "high_risk_accounts": [
            acc for acc, info in flags.items()
            if info["risk"] == "HIGH"
        ],
        "cash_withdrawals": stats["cash_withdrawals"],
        "reversal_count": stats["reversal_count"],
        "reversal_amount": stats["reversal_amount"]
    }

    print("Sending verified findings to Groq (Llama 3)...\n")
    brief = generate_investigation_brief(findings)
    print("Investigation Brief:")
    print("-" * 50)
    print(brief)
    print("-" * 50)
    print("\nBrief also saved to cached_brief.txt for offline use")