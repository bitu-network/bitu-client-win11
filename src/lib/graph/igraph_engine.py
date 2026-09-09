# file: src/lib/graph/igraph_engine.py

import igraph as ig

from lib.graph.graph_engine import GraphEngine

class IGraphEngine(GraphEngine):
    def __init__(self):
        self.g = ig.Graph()

    def add_edge(self, u, v, weight):
        self.g.add_vertices([u, v])
        self.g.add_edge(u, v, weight=weight)

    def shortest_path(self, src, dst):
        return self.g.get_shortest_paths(src, dst, weights="weight")[0]

    def widest_path(self, src, dst):
        # transform weights or use igraph facilities
        pass

    def mst(self):
        return self.g.spanning_tree(weights="weight")
