import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.graph import build_graph
from app.ingest import UnsupportedFileError, chunk_text, extract_text
from app.llm import LLM, ClaudeLLM
from app.vectorstore import VectorStore
from app.web import FetchError, fetch_page_text


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[Message] = []
    sources: list[str] | None = None


class UrlRequest(BaseModel):
    url: str


def create_app(llm: LLM | None = None, store: VectorStore | None = None) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        vs = store or VectorStore(settings.chroma_path, settings.collection_name)
        model = llm or ClaudeLLM(
            settings.anthropic_api_key, settings.claude_model, settings.max_tokens
        )
        app.state.store = vs
        app.state.graph = build_graph(model, vs, settings.top_k, settings.max_distance)
        yield

    app = FastAPI(title="RAG Chatbot", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "llm_configured": bool(llm or settings.anthropic_api_key)}

    @app.get("/api/documents")
    async def list_documents() -> list[dict[str, Any]]:
        sources = app.state.store.list_sources()
        return [{"source": s, "chunks": n} for s, n in sorted(sources.items())]

    @app.post("/api/documents")
    async def upload(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
        name = file.filename or "upload"
        try:
            text = extract_text(name, await file.read())
        except UnsupportedFileError as e:
            raise HTTPException(status_code=415, detail=str(e)) from e
        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise HTTPException(status_code=422, detail="No text found in file")
        app.state.store.delete_source(name)
        return {"source": name, "chunks": app.state.store.add(name, chunks)}

    @app.post("/api/documents/url")
    async def ingest_url(req: UrlRequest) -> dict[str, Any]:
        try:
            text = await fetch_page_text(req.url)
        except FetchError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise HTTPException(status_code=422, detail="No text found at URL")
        app.state.store.delete_source(req.url)
        return {"source": req.url, "chunks": app.state.store.add(req.url, chunks)}

    @app.delete("/api/documents/{source:path}")
    async def delete_document(source: str) -> dict[str, str]:
        app.state.store.delete_source(source)
        return {"deleted": source}

    @app.post("/api/chat")
    async def chat(req: ChatRequest) -> StreamingResponse:
        if not req.question.strip():
            raise HTTPException(status_code=422, detail="Question is empty")
        state = {
            "question": req.question,
            "history": [m.model_dump() for m in req.history],
            "sources": req.sources or [],
        }

        async def events() -> AsyncIterator[str]:
            try:
                async for chunk in app.state.graph.astream(state, stream_mode="custom"):
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    return app


app = create_app()
