# RAG Chatbot

Retrieval-augmented chatbot: **FastAPI** + **LangGraph** + **ChromaDB** + **Claude or Gemini**, with a **React** (Vite + TypeScript) frontend.

## How it works

Upload PDF/TXT/MD files → they are chunked and embedded into a persistent ChromaDB collection.
Each chat question runs through a LangGraph pipeline:

```
rewrite (standalone query from history) → retrieve (top-k from Chroma)
        → generate (Gemini, streamed, cites [1], [2]…)   if relevant hits
        → no_context (canned reply)                      otherwise
```

Answers stream to the UI over Server-Sent Events, along with the retrieved sources.
Embeddings use Chroma's built-in local model (all-MiniLM-L6-v2, downloaded on first use); The LLM (Gemini by default, or Claude) is used for generation and query rewriting.

**Choosing a provider:** `LLM_PROVIDER` defaults to `gemini` (needs `GEMINI_API_KEY`, optional `GEMINI_MODEL`); set `LLM_PROVIDER=anthropic` (needs `ANTHROPIC_API_KEY`) to use Claude.

## Features

- Upload PDF/TXT/MD (drag & drop) or ingest a public web page by URL (SSRF-guarded: public http(s) hosts only, no redirects, 5 MB cap)
- Restrict a question to selected documents
- Streaming answers rendered as Markdown with inline `[n]` citations and expandable source passages
- Conversation memory (follow-ups are rewritten into standalone queries), persisted in the browser; New chat, Copy, Regenerate, Stop
- Warning banner when the backend is down or the LLM API key is missing; dark mode

## Run

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                  # set GEMINI_API_KEY
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to :8000
```

## Deploying

- **Backend** (FastAPI + ChromaDB) needs a host with a persistent disk. A `Dockerfile` is provided — mount a volume at `/chroma_data`. Set `CORS_ORIGINS` to your frontend origin and, optionally, `APP_API_KEY`.
- **Frontend** (Vite) builds to static files. Deploy `frontend/` to Netlify/Vercel and set `VITE_API_URL` to your backend URL (and `VITE_API_KEY` to match `APP_API_KEY`). A `netlify.toml` is included.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | liveness + `llm_configured` |
| GET/POST | `/api/documents` | list / upload (multipart `file`) |
| POST | `/api/documents/url` | `{url}` → fetch and index a web page |
| DELETE | `/api/documents/{source}` | remove a document |
| POST | `/api/chat` | `{question, history, sources?}` → SSE events (`sources`, `token`, `error`, `done`) |

## Quality checks

```bash
cd backend  && ruff check . && ruff format --check . && mypy app tests && pytest
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

The same checks run in GitHub Actions (`.github/workflows/ci.yml`).
