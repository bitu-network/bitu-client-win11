# file: src/graph.py
# File Purpose: Provides a utility function to load a localized graph subgraph from an SQLite database into a graph processing engine up to a specified hop distance.
# Database Connection: Connects to an SQLite database located at sqlite_path and queries edge records (u, v, weight) filtered by a maximum hop horizon (hops <= horizon).
# Engine Initialization: Instantiates a GraphEngine (or an equivalent graph backend) and populates it dynamically by adding each retrieved edge and its weight.
# Return Value: Returns the fully constructed and populated GraphEngine instance representing the targeted subgraph.


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