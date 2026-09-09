# file: src/lib/graph/graph_engine.py

class GraphEngine:
    def add_edge(self, u, v, weight):
        raise NotImplementedError

    def shortest_path(self, src, dst):
        raise NotImplementedError

    def widest_path(self, src, dst):
        raise NotImplementedError

    def mst(self):
        raise NotImplementedError
