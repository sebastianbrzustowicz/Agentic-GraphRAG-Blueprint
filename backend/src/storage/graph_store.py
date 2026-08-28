import os
import pickle

import networkx as nx

from src.storage.base import AbstractGraphStore


class NetworkXGraphStore(AbstractGraphStore):
    def __init__(self) -> None:
        self._graph = nx.MultiDiGraph()

    def add_node(self, node_id: str, **attributes) -> None:
        if node_id in self._graph:
            self._graph.nodes[node_id].update(attributes)
        else:
            self._graph.add_node(node_id, **attributes)

    def add_edge(self, source: str, target: str, **attributes) -> None:
        self._graph.add_edge(source, target, **attributes)

    def get_neighbors(self, node_id: str) -> list[str]:
        if node_id not in self._graph:
            return []
        neighbors = set(self._graph.successors(node_id))
        neighbors.update(self._graph.predecessors(node_id))
        return sorted(neighbors)

    def get_subgraph(self, node_ids: list[str], radius: int = 1) -> dict:
        seeds = [node for node in node_ids if node in self._graph]
        selected = set(seeds)
        frontier = set(seeds)
        for _ in range(radius):
            next_frontier: set[str] = set()
            for node in frontier:
                next_frontier.update(self._graph.successors(node))
                next_frontier.update(self._graph.predecessors(node))
            frontier = next_frontier - selected
            selected.update(next_frontier)
        subgraph = self._graph.subgraph(selected)
        nodes = [{"id": node, **dict(subgraph.nodes[node])} for node in subgraph.nodes]
        edges = [
            {"source": source, "target": target, **dict(attributes)}
            for source, target, attributes in subgraph.edges(data=True)
        ]
        return {"nodes": nodes, "edges": edges}

    def get_all_nodes(self) -> list[dict]:
        return [{"id": node, **dict(self._graph.nodes[node])} for node in self._graph.nodes]

    def get_all_edges(self) -> list[dict]:
        return [
            {"source": source, "target": target, **dict(attributes)}
            for source, target, attributes in self._graph.edges(data=True)
        ]

    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def reset(self) -> None:
        self._graph = nx.MultiDiGraph()

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as handle:
            pickle.dump(self._graph, handle)

    def load(self, path: str) -> None:
        with open(path, "rb") as handle:
            self._graph = pickle.load(handle)
