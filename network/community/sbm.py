"""Optional graph-tool backend. Never substitutes another algorithm for SBM."""
from collections import defaultdict


def fit_weekly(edge_rows, seed=42):
    try:
        import graph_tool.all as gt
    except ImportError as exc:
        raise RuntimeError("--sbm requires graph-tool in a supported Linux/WSL environment") from exc
    grouped = defaultdict(list)
    for row in edge_rows:
        grouped[row["week"]].append(row)
    memberships, models = [], []
    for week, edges in sorted(grouped.items()):
        gt.seed_rng(seed)
        nodes = sorted({e[k] for e in edges for k in ("source", "target")})
        index = {u: i for i, u in enumerate(nodes)}
        graph = gt.Graph(directed=True)
        graph.add_vertex(len(nodes))
        weight = graph.new_edge_property("int")
        for row in edges:
            edge = graph.add_edge(index[row["source"]], index[row["target"]])
            weight[edge] = row["weight"]
        state = gt.minimize_blockmodel_dl(graph, state_args={"deg_corr": True, "eweight": weight})
        blocks = state.get_blocks()
        for user, i in index.items():
            memberships.append(dict(week=week, user_id=user, block=int(blocks[graph.vertex(i)])))
        models.append(dict(week=week, nodes=len(nodes), edges=sum(e["weight"] for e in edges),
                           description_length=float(state.entropy()),
                           blocks=len({r["block"] for r in memberships if r["week"] == week})))
    return memberships, models
