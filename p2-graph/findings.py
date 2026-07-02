import json
from test_data import get_mock_transactions
from graph_engine import build_transaction_graph, detect_round_trips, flag_suspicious_nodes
from fifo_trail import trace_fifo_trail
from analytics import generate_analytics
from ai_brief import generate_investigation_brief


def get_full_findings(df) -> dict:
    """
    Master function — takes a dataframe, returns everything.
    This is what FastAPI will call and Person 3's frontend will consume.
    """

    # Step 1: Analytics
    stats = generate_analytics(df)

    # Step 2: Build graph (reversals already excluded inside)
    G = build_transaction_graph(df)

    # Step 3: Round trip detection
    round_trips = detect_round_trips(G)

    # Step 4: Flag suspicious nodes
    flags = flag_suspicious_nodes(G, round_trips)

    # Step 5: FIFO trail for all high risk accounts
    fifo_trails = {}
    high_risk = [acc for acc, info in flags.items() if info["risk"] == "HIGH"]
    for account in high_risk:
        fifo_trails[account] = trace_fifo_trail(df, account)

    # Step 6: Build verified findings for AI
    verified_findings = {
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
        "high_risk_accounts": high_risk,
        "cash_withdrawals": stats["cash_withdrawals"],
        "reversal_count": stats["reversal_count"],
        "reversal_amount": stats["reversal_amount"]
    }

    # Step 7: AI brief
    ai_brief = generate_investigation_brief(verified_findings)

    # Step 8: Build graph data for frontend (Person 3 needs this for React Flow)
    graph_nodes = []
    for node in G.nodes:
        info = flags.get(node, {})
        graph_nodes.append({
            "id": node,
            "risk": info.get("risk", "LOW"),
            "total_sent": info.get("total_sent", 0),
            "total_received": info.get("total_received", 0),
            "in_round_trip": info.get("in_round_trip", False)
        })

    graph_edges = []
    for from_node, to_node, data in G.edges(data=True):
        graph_edges.append({
            "from": from_node,
            "to": to_node,
            "amount": data["amount"],
            "txn_count": data["txn_count"]
        })

    return {
        "analytics": stats,
        "round_trips": round_trips,
        "node_flags": flags,
        "fifo_trails": fifo_trails,
        "ai_brief": ai_brief,
        "graph": {
            "nodes": graph_nodes,
            "edges": graph_edges
        }
    }


if __name__ == "__main__":
    df = get_mock_transactions()
    results = get_full_findings(df)

    print("=" * 60)
    print("FULL FINDINGS SUMMARY")
    print("=" * 60)

    print(f"\nTotal transactions   : {results['analytics']['total_transactions']}")
    print(f"Reversals excluded   : {results['analytics']['reversal_count']}")
    print(f"Total amount moved   : Rs.{results['analytics']['total_amount_moved']:,.0f}")
    print(f"Cash withdrawals     : {results['analytics']['cash_withdrawals']}")

    print(f"\nRound trips found    : {len(results['round_trips'])}")
    for rt in results['round_trips']:
        print(f"  {rt['cycle_str']}")
        print(f"  Amount: Rs.{rt['total_amount']:,} | Layers: {rt['layer']}")

    print(f"\nHigh risk accounts   : {[n for n,i in results['node_flags'].items() if i['risk']=='HIGH']}")

    print(f"\nGraph nodes          : {len(results['graph']['nodes'])}")
    print(f"Graph edges          : {len(results['graph']['edges'])}")

    print(f"\nFIFO trails computed : {list(results['fifo_trails'].keys())}")

    print(f"\nAI Brief preview:")
    print("-" * 60)
    print(results['ai_brief'][:300] + "...")

    print("\nSaving full findings to findings_output.json...")
    with open("findings_output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print("Saved to findings_output.json")