import hashlib
import uuid
from collections.abc import AsyncIterator
from typing import Any, cast

import chromadb
import pytest
from chromadb import Documents, EmbeddingFunction, Embeddings

from app.vectorstore import VectorStore


class HashEmbedding(EmbeddingFunction[Documents]):
    """Deterministic bag-of-words embedding so tests need no model download."""

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:
        out = []
        for text in input:
            vec = [0.0] * 64
            for word in text.lower().split():
                vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % 64] += 1.0
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            out.append([v / norm for v in vec])
        return cast(Embeddings, out)

    def get_config(self) -> dict[str, Any]:
        return {}

    @staticmethod
    def name() -> str:
        return "hash-embedding"


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        return "standalone query"

    async def stream(self, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        self.calls.append(messages)
        for tok in ["Hello", " world"]:
            yield tok


@pytest.fixture
def store() -> VectorStore:
    return VectorStore(
        path="",
        collection=f"t{uuid.uuid4().hex}",
        embedding_function=HashEmbedding(),
        client=chromadb.EphemeralClient(),
    )


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()
