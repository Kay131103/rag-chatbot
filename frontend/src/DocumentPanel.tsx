import { useCallback, useEffect, useRef, useState } from "react";
import { deleteDocument, listDocuments, uploadDocument, type DocumentInfo } from "./api";

export default function DocumentPanel() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setDocs(await listDocuments());
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function onUpload(files: FileList | null) {
    if (!files) return;
    setBusy(true);
    setError(null);
    try {
      for (const f of Array.from(files)) await uploadDocument(f);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
      await refresh();
    }
  }

  async function onDelete(source: string) {
    try {
      await deleteDocument(source);
    } catch (e) {
      setError((e as Error).message);
    }
    await refresh();
  }

  return (
    <aside className="panel">
      <h2>Knowledge base</h2>
      <label className="upload">
        {busy ? "Uploading…" : "Upload PDF / TXT / MD"}
        <input
          ref={input}
          type="file"
          multiple
          accept=".pdf,.txt,.md,.markdown"
          disabled={busy}
          onChange={(e) => void onUpload(e.target.files)}
        />
      </label>
      {error && <p className="error">{error}</p>}
      <ul>
        {docs.map((d) => (
          <li key={d.source}>
            <span>
              {d.source} <small>({d.chunks} chunks)</small>
            </span>
            <button aria-label={`Delete ${d.source}`} onClick={() => void onDelete(d.source)}>
              ✕
            </button>
          </li>
        ))}
        {docs.length === 0 && <li className="empty">No documents yet.</li>}
      </ul>
    </aside>
  );
}
