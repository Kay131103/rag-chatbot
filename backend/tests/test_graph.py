from typing import Any

from app.graph import NO_CONTEXT_ANSWER, build_graph, format_context
from app.vectorstore import Hit, VectorStore
from tests.conftest import FakeLLM


async def _run(graph: Any, state: dict[str, Any]) -> list[dict[str, Any]]:
    return [chunk async for chunk in graph.astream(state, stream_mode="custom")]


def test_format_context_numbers_blocks() -> None:
    text = format_context([Hit("alpha", "a.txt", 0.1), Hit("beta", "b.txt", 0.2)])
    assert text == "[1] (source: a.txt)\nalpha\n\n[2] (source: b.txt)\nbeta"


async def test_generates_answer_when_hits_found(store: VectorStore, llm: FakeLLM) -> None:
    store.add("d.txt", ["red apples grow on trees"])
    graph = build_graph(llm, store, top_k=3, max_distance=1.2)
    events = await _run(graph, {"question": "red apples grow on trees"})
    assert events[0]["type"] == "sources"
    assert "".join(e["text"] for e in events if e["type"] == "token") == "Hello world"
    prompt = llm.calls[0][-1]["content"]
    assert "red apples grow on trees" in prompt
    assert "Question: red apples grow on trees" in prompt


async def test_no_context_when_store_empty(store: VectorStore, llm: FakeLLM) -> None:
    graph = build_graph(llm, store, top_k=3, max_distance=1.2)
    events = await _run(graph, {"question": "hello"})
    texts = [e["text"] for e in events if e["type"] == "token"]
    assert texts == [NO_CONTEXT_ANSWER]
    assert llm.calls == []


async def test_distance_threshold_drops_irrelevant_hits(store: VectorStore, llm: FakeLLM) -> None:
    store.add("d.txt", ["completely unrelated words"])
    graph = build_graph(llm, store, top_k=3, max_distance=0.01)
    events = await _run(graph, {"question": "zebra"})
    assert events[0] == {"type": "sources", "sources": []}
    assert llm.calls == []


async def test_history_is_rewritten_and_forwarded(store: VectorStore, llm: FakeLLM) -> None:
    store.add("d.txt", ["standalone query"])
    graph = build_graph(llm, store, top_k=3, max_distance=1.2)
    history = [{"role": "user", "content": "earlier"}, {"role": "assistant", "content": "reply"}]
    await _run(graph, {"question": "and then?", "history": history})
    sent = llm.calls[0]
    assert sent[:2] == history
    assert sent[-1]["role"] == "user"


async def test_source_filter_is_applied(store: VectorStore, llm: FakeLLM) -> None:
    store.add("a.txt", ["same text"])
    store.add("b.txt", ["same text"])
    graph = build_graph(llm, store, top_k=5, max_distance=1.2)
    events = await _run(graph, {"question": "same text", "sources": ["a.txt"]})
    assert {s["source"] for s in events[0]["sources"]} == {"a.txt"}
