import { useRef, useState, type FormEvent } from "react";
import { streamChat, type Message, type Source } from "./api";

interface Turn extends Message {
  sources?: Source[];
}

export default function Chat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const abort = useRef<AbortController | null>(null);

  function updateLast(fn: (t: Turn) => Turn) {
    setTurns((prev) => [...prev.slice(0, -1), fn(prev[prev.length - 1])]);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;
    const history: Message[] = turns.map(({ role, content }) => ({ role, content }));
    setTurns([...turns, { role: "user", content: q }, { role: "assistant", content: "" }]);
    setQuestion("");
    setLoading(true);
    abort.current = new AbortController();
    try {
      await streamChat(
        q,
        history,
        (ev) => {
          if (ev.type === "token") updateLast((t) => ({ ...t, content: t.content + ev.text }));
          else if (ev.type === "sources") updateLast((t) => ({ ...t, sources: ev.sources }));
          else if (ev.type === "error")
            updateLast((t) => ({ ...t, content: `${t.content}\nError: ${ev.message}` }));
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

  return (
    <main className="chat">
      <div className="messages">
        {turns.length === 0 && <p className="empty">Upload documents, then ask a question.</p>}
        {turns.map((t, i) => (
          <div key={i} className={`msg ${t.role}`}>
            <div className="bubble">{t.content || (loading ? "…" : "")}</div>
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
      </div>
      <form onSubmit={(e) => void onSubmit(e)}>
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
