import networkx as nx
import pandas as pd


def build_transaction_graph(df: pd.DataFrame) -> nx.DiGraph:
    G = nx.DiGraph()

    clean = df[df["is_reversal"] == False].copy()

    for _, row in clean.iterrows():
        from_acc = row["from_account"]
        to_acc = row["to_account"]
        amount = row["amount"]

        if from_acc not in G.nodes:
            G.add_node(from_acc, total_sent=0, total_received=0)
        if to_acc not in G.nodes:
            G.add_node(to_acc, total_sent=0, total_received=0)

        G.nodes[from_acc]["total_sent"] += amount
        G.nodes[to_acc]["total_received"] += amount

        if G.has_edge(from_acc, to_acc):
            G[from_acc][to_acc]["amount"] += amount
            G[from_acc][to_acc]["txn_count"] += 1
        else:
            G.add_edge(from_acc, to_acc, amount=amount, txn_count=1)

    return G


def detect_round_trips(G: nx.DiGraph) -> list:
    results = []

    try:
        cycles = []
        for cycle in nx.simple_cycles(G):
            if len(cycle) < 2:
                continue
            if len(cycle) > 6:
                continue
            cycles.append(cycle)
            if len(cycles) >= 50:
                break
    except Exception as e:
        print(f"Cycle detection error: {e}")
        return []

    for cycle in cycles:
        total_amount = 0
        edges_in_cycle = []

        for i in range(len(cycle)):
            from_node = cycle[i]
            to_node = cycle[(i + 1) % len(cycle)]

            if G.has_edge(from_node, to_node):
                edge_data = G[from_node][to_node]
                total_amount += edge_data["amount"]
                edges_in_cycle.append({
                    "from": from_node,
                    "to": to_node,
                    "amount": edge_data["amount"]
                })

        results.append({
            "cycle": cycle,
            "cycle_str": " → ".join(cycle) + f" → {cycle[0]}",
            "total_amount": total_amount,
            "layer": len(cycle) - 1,
            "hops": len(cycle),
            "edges": edges_in_cycle
        })

    results.sort(key=lambda x: x["total_amount"], reverse=True)
    return results
def flag_suspicious_nodes(G: nx.DiGraph, round_trips: list) -> dict:
    flagged = set()
    for rt in round_trips:
        for account in rt["cycle"]:
            flagged.add(account)

    flags = {}
    for node in G.nodes:
        data = G.nodes[node]
        sent = data.get("total_sent", 0)
        received = data.get("total_received", 0)
        velocity = sent / received if received > 0 else 0

        if node in flagged:
            risk = "HIGH"
        elif velocity > 0.8:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        flags[node] = {
            "risk": risk,
            "total_sent": sent,
            "total_received": received,
            "velocity_ratio": round(velocity, 2),
            "in_round_trip": node in flagged
        }

    return flags


if __name__ == "__main__":
    from test_data import get_mock_transactions

    df = get_mock_transactions()
    G = build_transaction_graph(df)

    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    round_trips = detect_round_trips(G)
    print(f"\n Round trips found: {len(round_trips)}")
    for rt in round_trips:
        print(f"  {rt['cycle_str']}")
        print(f"  Amount: ₹{rt['total_amount']:,} | Layers: {rt['layer']}")

    flags = flag_suspicious_nodes(G, round_trips)
    print(f"\nAccount risk levels:")
    for acc, info in flags.items():
        print(f"  {acc}: {info['risk']} | sent ₹{info['total_sent']:,} | received ₹{info['total_received']:,}")