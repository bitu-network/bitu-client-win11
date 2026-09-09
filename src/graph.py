# file: src/graph.py

import sqlite3
from lib.graph.graph_engine import GraphEngine

def load_subgraph(sqlite_path: str, horizon: int) -> GraphEngine:
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    edges = cur.execute(
        "SELECT u, v, weight FROM edges WHERE hops <= ?", (horizon,)
    ).fetchall()
    conn.close()

    engine = GraphEngine()  # or IGraphBackend() if using igraph
    for u, v, w in edges:
        engine.add_edge(u, v, w)
    return engine