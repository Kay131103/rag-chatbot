from typing import Any, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.llm import LLM
from app.vectorstore import Hit, VectorStore

REWRITE_SYSTEM = (
    "Rewrite the user's latest question as a standalone search query, using the chat history "
    "for context. Reply with the query only."
)
ANSWER_SYSTEM = (
    "You are a helpful assistant that answers strictly from the provided context. "
    "Cite sources inline like [1], [2] matching the numbered context blocks. "
    "If the context does not contain the answer, say you don't know."
)
NO_CONTEXT_ANSWER = (
    "I couldn't find anything relevant in the knowledge base. Try uploading documents first."
)


class RAGState(TypedDict, total=False):
    question: str
    history: list[dict[str, str]]
    query: str
    hits: list[Hit]
    answer: str


def format_context(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{i}] (source: {h.source})\n{h.text}" for i, h in enumerate(hits, 1))


def build_graph(llm: LLM, store: VectorStore, top_k: int, max_distance: float) -> Any:
    async def rewrite(state: RAGState) -> dict[str, Any]:
        history = state.get("history", [])
        if not history:
            return {"query": state["question"]}
        msgs = [*history, {"role": "user", "content": state["question"]}]
        query = (await llm.complete(REWRITE_SYSTEM, msgs)).strip()
        return {"query": query or state["question"]}

    async def retrieve(state: RAGState) -> dict[str, Any]:
        hits = [h for h in store.search(state["query"], top_k) if h.distance <= max_distance]
        get_stream_writer()({"type": "sources", "sources": [_hit_dict(h) for h in hits]})
        return {"hits": hits}

    async def generate(state: RAGState) -> dict[str, Any]:
        writer = get_stream_writer()
        prompt = f"Context:\n{format_context(state['hits'])}\n\nQuestion: {state['question']}"
        msgs = [*state.get("history", []), {"role": "user", "content": prompt}]
        parts: list[str] = []
        async for token in llm.stream(ANSWER_SYSTEM, msgs):
            parts.append(token)
            writer({"type": "token", "text": token})
        return {"answer": "".join(parts)}

    async def no_context(state: RAGState) -> dict[str, Any]:
        get_stream_writer()({"type": "token", "text": NO_CONTEXT_ANSWER})
        return {"answer": NO_CONTEXT_ANSWER}

    def route(state: RAGState) -> str:
        return "generate" if state.get("hits") else "no_context"

    g: StateGraph[RAGState, None, RAGState, RAGState] = StateGraph(RAGState)
    g.add_node("rewrite", rewrite)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_node("no_context", no_context)
    g.add_edge(START, "rewrite")
    g.add_edge("rewrite", "retrieve")
    g.add_conditional_edges("retrieve", route, ["generate", "no_context"])
    g.add_edge("generate", END)
    g.add_edge("no_context", END)
    return g.compile()


def _hit_dict(h: Hit) -> dict[str, Any]:
    return {"source": h.source, "text": h.text, "distance": h.distance}
