import uuid
from dataclasses import dataclass
from typing import Any

import chromadb
from chromadb.api.types import EmbeddingFunction


@dataclass(frozen=True)
class Hit:
    text: str
    source: str
    distance: float


class VectorStore:
    """Thin wrapper around a persistent ChromaDB collection."""

    def __init__(
        self,
        path: str,
        collection: str,
        embedding_function: EmbeddingFunction[Any] | None = None,
        client: Any = None,
    ) -> None:
        self._client = client or chromadb.PersistentClient(path=path)
        kwargs: dict[str, Any] = {"name": collection}
        if embedding_function is not None:
            kwargs["embedding_function"] = embedding_function
        self._col = self._client.get_or_create_collection(**kwargs)

    def add(self, source: str, chunks: list[str]) -> int:
        if not chunks:
            return 0
        self._col.add(
            ids=[str(uuid.uuid4()) for _ in chunks],
            documents=chunks,
            metadatas=[{"source": source, "chunk": i} for i in range(len(chunks))],
        )
        return len(chunks)

    def search(self, query: str, k: int) -> list[Hit]:
        if self._col.count() == 0:
            return []
        res = self._col.query(query_texts=[query], n_results=k)
        docs = (res["documents"] or [[]])[0]
        metas = (res["metadatas"] or [[]])[0]
        dists = (res["distances"] or [[]])[0]
        return [
            Hit(text=d, source=str((m or {}).get("source", "unknown")), distance=float(x))
            for d, m, x in zip(docs, metas, dists, strict=False)
        ]

    def list_sources(self) -> dict[str, int]:
        data = self._col.get(include=["metadatas"])
        counts: dict[str, int] = {}
        for meta in data["metadatas"] or []:
            src = str(meta.get("source", "unknown"))
            counts[src] = counts.get(src, 0) + 1
        return counts

    def delete_source(self, source: str) -> None:
        self._col.delete(where={"source": source})
