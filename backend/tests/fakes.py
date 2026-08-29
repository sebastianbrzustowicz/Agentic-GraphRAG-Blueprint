import json
from types import SimpleNamespace
from typing import Any

from src.storage.base import AbstractGraphStore, AbstractVectorStore


class FakeGraphStore(AbstractGraphStore):
    """In-memory graph store for tests."""

    def __init__(self) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []

    def add_node(self, node_id: str, **attributes: Any) -> None:
        self._nodes.setdefault(node_id, {"id": node_id})
        self._nodes[node_id].update(attributes)

    def add_edge(self, source: str, target: str, **attributes: Any) -> None:
        self._edges.append({"source": source, "target": target, **attributes})

    def get_neighbors(self, node_id: str) -> list[str]:
        neighbors = []
        for edge in self._edges:
            if edge["source"] == node_id:
                neighbors.append(edge["target"])
            if edge["target"] == node_id:
                neighbors.append(edge["source"])
        return neighbors

    def get_subgraph(self, node_ids: list[str], radius: int = 1) -> dict[str, Any]:
        include = set(node_ids)
        frontier = set(node_ids)
        for _ in range(radius):
            next_frontier = set()
            for node in frontier:
                next_frontier.update(self.get_neighbors(node))
            include.update(next_frontier)
            frontier = next_frontier
        nodes = [self._nodes.get(node, {"id": node}) for node in include]
        edges = [
            edge for edge in self._edges if edge["source"] in include and edge["target"] in include
        ]
        return {"nodes": nodes, "edges": edges}

    def get_all_nodes(self) -> list[dict[str, Any]]:
        return list(self._nodes.values())

    def get_all_edges(self) -> list[dict[str, Any]]:
        return list(self._edges)

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def reset(self) -> None:
        self._nodes = {}
        self._edges = []

    def save(self, path: str) -> None:  # noqa: ARG002 - no-op for tests
        pass

    def load(self, path: str) -> None:  # noqa: ARG002 - no-op for tests
        pass


class FakeVectorStore(AbstractVectorStore):
    """In-memory vector store that scores documents by token overlap."""

    def __init__(self) -> None:
        self._documents: list[dict[str, Any]] = []

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        metadata_list = metadatas or [{} for _ in documents]
        for doc_id, document, metadata in zip(ids, documents, metadata_list, strict=True):
            self._documents.append({"id": doc_id, "text": document, "metadata": metadata})

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        hits = []
        for doc in self._documents:
            if where and not all(doc["metadata"].get(key) == value for key, value in where.items()):
                continue
            overlap = len(set(query.split()) & set(doc["text"].split()))
            hits.append({**doc, "score": float(overlap)})
        hits.sort(key=lambda hit: hit["score"], reverse=True)
        return hits[:k]

    def count(self) -> int:
        return len(self._documents)

    def reset(self) -> None:
        self._documents = []

    def delete(self, ids: list[str]) -> None:
        self._documents = [doc for doc in self._documents if doc["id"] not in set(ids)]


class FakeOpenAI:
    """Minimal OpenAI client stand-in returning canned chat completions.

    In ``batched`` mode the response is generated from the request: one chunk entry
    per ``---CHUNK`` marker found in the user message.
    """

    def __init__(self, chat_content: str | dict, batched: bool = False) -> None:
        self.chat = _Chat(chat_content, batched)

    @property
    def calls(self) -> int:
        return self.chat.completions.calls


class _Chat:
    def __init__(self, content: str | dict, batched: bool) -> None:
        self.completions = _Completions(content, batched)


class _Completions:
    def __init__(self, content: str | dict, batched: bool) -> None:
        self._batched = batched
        self.calls = 0
        if isinstance(content, dict):
            content = json.dumps(content)
        self._content = content

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls += 1
        user = ""
        for message in kwargs.get("messages", []):
            if message.get("role") == "user":
                user = message.get("content", "")
        if self._batched and "---CHUNK" in user:
            count = user.count("---CHUNK")
            payload = {
                "chunks": [
                    {
                        "chunk_index": index,
                        "entities": [{"name": f"Entity{index}", "type": "protein", "description": f"desc {index}"}],
                        "relations": [],
                    }
                    for index in range(count)
                ]
            }
            content = json.dumps(payload)
        else:
            content = self._content
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )
