from abc import ABC, abstractmethod
from typing import Any


class AbstractGraphStore(ABC):
    @abstractmethod
    def add_node(self, node_id: str, **attributes: Any) -> None: ...

    @abstractmethod
    def add_edge(self, source: str, target: str, **attributes: Any) -> None: ...

    @abstractmethod
    def get_neighbors(self, node_id: str) -> list[str]: ...

    @abstractmethod
    def get_subgraph(self, node_ids: list[str], radius: int = 1) -> dict[str, Any]: ...

    @abstractmethod
    def get_all_nodes(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_all_edges(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def node_count(self) -> int: ...

    @abstractmethod
    def edge_count(self) -> int: ...

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def save(self, path: str) -> None: ...

    @abstractmethod
    def load(self, path: str) -> None: ...


class AbstractVectorStore(ABC):
    @abstractmethod
    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None: ...

    @abstractmethod
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def reset(self) -> None: ...
