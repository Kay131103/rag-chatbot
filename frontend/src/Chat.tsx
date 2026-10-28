import { useEffect, useRef, useState, type FormEvent } from "react";
import Markdown from "react-markdown";
import { streamChat, type Message, type Source } from "./api";

interface Turn extends Message {
  sources?: Source[];
}

const STORAGE_KEY = "rag-chat-turns";

function loadTurns(): Turn[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as Turn[];
  } catch {
    return [];
  }
}

export default function Chat({ sources }: { sources: string[] }) {
  const [turns, setTurns] = useState<Turn[]>(loadTurns);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!loading) localStorage.setItem(STORAGE_KEY, JSON.stringify(turns));
    bottom.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [turns, loading]);

  function updateLast(fn: (t: Turn) => Turn) {
    setTurns((prev) => [...prev.slice(0, -1), fn(prev[prev.length - 1])]);
  }

  async function ask(q: string, base: Turn[]) {
    const history: Message[] = base.map(({ role, content }) => ({ role, content }));
    setTurns([...base, { role: "user", content: q }, { role: "assistant", content: "" }]);
    setLoading(true);
    abort.current = new AbortController();
    try {
      await streamChat(
        q,
        history,
        sources,
        (ev) => {
          if (ev.type === "token") updateLast((t) => ({ ...t, content: t.content + ev.text }));
          else if (ev.type === "sources") updateLast((t) => ({ ...t, sources: ev.sources }));
          else if (ev.type === "error")
            updateLast((t) => ({ ...t, content: `${t.content}\n\nError: ${ev.message}` }));
        },
        abort.current.signal,
      );
    } catch (err) {
      if ((err as Error).name !== "AbortError")
        updateLast((t) => ({ ...t, content: `Error: ${(err as Error).message}` }));
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;
    setQuestion("");
    void ask(q, turns);
  }

  function regenerate() {
    const lastUser = turns[turns.length - 2];
    if (loading || !lastUser) return;
    void ask(lastUser.content, turns.slice(0, -2));
  }

  function newChat() {
    abort.current?.abort();
    setTurns([]);
  }

  return (
    <main className="chat">
      <header>
        <h1>RAG Chatbot</h1>
        <button onClick={newChat} disabled={turns.length === 0}>
          New chat
        </button>
      </header>
      <div className="messages">
        {turns.length === 0 && <p className="empty">Upload documents, then ask a question.</p>}
        {turns.map((t, i) => (
          <div key={i} className={`msg ${t.role}`}>
            <div className="bubble">
              {t.role === "assistant" ? (
                <Markdown>{t.content || (loading ? "…" : "")}</Markdown>
              ) : (
                t.content
              )}
            </div>
            {t.role === "assistant" && t.content && !(loading && i === turns.length - 1) && (
              <div className="actions">
                <button onClick={() => void navigator.clipboard.writeText(t.content)}>Copy</button>
                {i === turns.length - 1 && <button onClick={regenerate}>Regenerate</button>}
              </div>
            )}
            {t.sources && t.sources.length > 0 && (
              <details>
                <summary>{t.sources.length} sources</summary>
                {t.sources.map((s, j) => (
                  <blockquote key={j}>
                    <strong>
                      [{j + 1}] {s.source}
                    </strong>
                    <p>{s.text}</p>
                  </blockquote>
                ))}
              </details>
            )}
          </div>
        ))}
        <div ref={bottom} />
      </div>
      <form onSubmit={onSubmit}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about your documents…"
          aria-label="Question"
        />
        <button type="submit" disabled={loading || !question.trim()}>
          Send
        </button>
        {loading && (
          <button type="button" onClick={() => abort.current?.abort()}>
            Stop
          </button>
        )}
      </form>
    </main>
  );
}
