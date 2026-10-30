import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.vectorstore import VectorStore
from tests.conftest import FakeLLM


def _events(body: str) -> list[dict[str, Any]]:
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]


def test_upload_list_chat_delete(store: VectorStore, llm: FakeLLM) -> None:
    with TestClient(create_app(llm=llm, store=store)) as client:
        assert client.get("/api/health").json() == {"status": "ok", "llm_configured": True}

        r = client.post(
            "/api/documents",
            files={"file": ("cats.txt", b"Cats are small carnivorous mammals.", "text/plain")},
        )
        assert r.status_code == 200
        assert r.json()["chunks"] == 1
        assert client.get("/api/documents").json() == [{"source": "cats.txt", "chunks": 1}]

        r = client.post("/api/chat", json={"question": "Cats are mammals?"})
        events = _events(r.text)
        assert events[0]["type"] == "sources"
        assert events[0]["sources"][0]["source"] == "cats.txt"
        assert "".join(e["text"] for e in events if e["type"] == "token") == "Hello world"
        assert events[-1] == {"type": "done"}

        assert client.delete("/api/documents/cats.txt").status_code == 200
        assert client.get("/api/documents").json() == []


def test_chat_without_documents(store: VectorStore, llm: FakeLLM) -> None:
    with TestClient(create_app(llm=llm, store=store)) as client:
        events = _events(client.post("/api/chat", json={"question": "anything"}).text)
        assert any(e["type"] == "token" for e in events)
        assert llm.calls == []


def test_chat_uses_history_rewrite(store: VectorStore, llm: FakeLLM) -> None:
    store.add("d.txt", ["standalone query answer text"])
    with TestClient(create_app(llm=llm, store=store)) as client:
        body = {"question": "and?", "history": [{"role": "user", "content": "hi"}]}
        events = _events(client.post("/api/chat", json=body).text)
        assert events[0]["type"] == "sources"


def test_upload_rejects_bad_type_and_empty(store: VectorStore, llm: FakeLLM) -> None:
    with TestClient(create_app(llm=llm, store=store)) as client:
        r = client.post("/api/documents", files={"file": ("x.exe", b"zz")})
        assert r.status_code == 415
        r = client.post("/api/documents", files={"file": ("x.txt", b"  ")})
        assert r.status_code == 422
        assert client.post("/api/chat", json={"question": " "}).status_code == 422


def test_source_filter_and_url_ingest(
    store: VectorStore, llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_fetch(url: str) -> str:
        return "Dogs are loyal domestic animals."

    monkeypatch.setattr("app.main.fetch_page_text", fake_fetch)
    store.add("cats.txt", ["Cats are small mammals."])
    with TestClient(create_app(llm=llm, store=store)) as client:
        r = client.post("/api/documents/url", json={"url": "https://example.com/dogs"})
        assert r.json() == {"source": "https://example.com/dogs", "chunks": 1}
        body = {"question": "Cats are small mammals.", "sources": ["cats.txt"]}
        events = _events(client.post("/api/chat", json=body).text)
        assert {s["source"] for s in events[0]["sources"]} == {"cats.txt"}
        deleted = client.delete("/api/documents/https://example.com/dogs")
        assert deleted.status_code == 200
        assert client.get("/api/health").json()["llm_configured"] is True


def test_url_ingest_error(store: VectorStore, llm: FakeLLM) -> None:
    with TestClient(create_app(llm=llm, store=store)) as client:
        assert client.post("/api/documents/url", json={"url": "ftp://x"}).status_code == 400


def test_api_key_enforced(
    store: VectorStore, llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_API_KEY", "s3cret")
    get_settings.cache_clear()
    try:
        with TestClient(create_app(llm=llm, store=store)) as client:
            assert client.get("/api/documents").status_code == 401
            assert client.get("/api/documents", headers={"X-API-Key": "wrong"}).status_code == 401
            assert client.get("/api/documents", headers={"X-API-Key": "s3cret"}).status_code == 200
            # health stays public
            assert client.get("/api/health").status_code == 200
    finally:
        get_settings.cache_clear()
