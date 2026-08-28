import time

import chromadb
from openai import APIConnectionError, APITimeoutError, NotFoundError, OpenAI, RateLimitError

from src.config import Config
from src.storage.base import AbstractVectorStore

RETRYABLE = (NotFoundError, APIConnectionError, APITimeoutError, RateLimitError)


def _retry_call(fn, *args, attempts: int = 4, delay: float = 1.0, **kwargs):
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn(*args, **kwargs)
        except RETRYABLE as exc:
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(delay * (2**attempt))
    assert last_exc is not None
    raise last_exc


class ChromaVectorStore(AbstractVectorStore):
    COLLECTION_NAME = "graphrag"

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = chromadb.PersistentClient(path=config.chroma_dir)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._embed_client = OpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url or None,
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = _retry_call(
            self._embed_client.embeddings.create,
            model=self._config.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict] | None = None,
    ) -> None:
        if not documents:
            return
        metadata_list = metadatas or [{} for _ in documents]
        embeddings = self._embed(documents)
        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadata_list,
            embeddings=embeddings,
        )

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        size = self._collection.count()
        if size == 0:
            return []
        limit = min(k, size)
        query_embedding = self._embed([query])[0]
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where,
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        hits = []
        for index, item_id in enumerate(ids):
            distance = distances[index] if distances else None
            score = 1.0 - distance if distance is not None else 0.0
            hits.append(
                {
                    "id": item_id,
                    "text": documents[index] if documents else "",
                    "metadata": metadatas[index] if metadatas else {},
                    "score": score,
                }
            )
        return hits

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        try:
            self._client.delete_collection(self.COLLECTION_NAME)
        except Exception:
            pass
        self._collection = self._client.create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
