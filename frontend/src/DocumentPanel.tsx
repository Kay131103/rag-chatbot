import { useCallback, useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import { addUrl, deleteDocument, listDocuments, uploadDocument, type DocumentInfo } from "./api";

interface Props {
  selected: string[];
  onSelectedChange: (sources: string[]) => void;
}

export default function DocumentPanel({ selected, onSelectedChange }: Props) {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState("");
  const input = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const list = await listDocuments();
      setDocs(list);
      onSelectedChange(selected.filter((s) => list.some((d) => d.source === s)));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [onSelectedChange, selected]);

  useEffect(() => {
    void refresh();
    // Refresh once on mount; later refreshes are triggered by user actions.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run(task: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await task();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
      await refresh();
    }
  }

  const onFiles = (files: FileList | null) =>
    files && run(() => Promise.all(Array.from(files).map(uploadDocument)));

  function onDrop(e: DragEvent) {
    e.preventDefault();
    void onFiles(e.dataTransfer.files);
  }

  function onUrl(e: FormEvent) {
    e.preventDefault();
    const target = url.trim();
    if (!target) return;
    setUrl("");
    void run(() => addUrl(target));
  }

  function toggle(source: string) {
    onSelectedChange(
      selected.includes(source) ? selected.filter((s) => s !== source) : [...selected, source],
    );
  }

  return (
    <aside className="panel">
      <h2>Knowledge base</h2>
      <label className="upload" onDragOver={(e) => e.preventDefault()} onDrop={onDrop}>
        {busy ? "Working…" : "Drop or click to upload PDF / TXT / MD"}
        <input
          ref={input}
          type="file"
          multiple
          accept=".pdf,.txt,.md,.markdown"
          disabled={busy}
          onChange={(e) => void onFiles(e.target.files)}
        />
      </label>
      <form className="url-form" onSubmit={onUrl}>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://… add a web page"
          aria-label="Page URL"
        />
        <button type="submit" disabled={busy || !url.trim()}>
          Add
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {docs.length > 0 && (
        <p className="hint">
          {selected.length === 0
            ? "Searching all documents. Tick to restrict."
            : `Searching ${selected.length} selected.`}
        </p>
      )}
      <ul>
        {docs.map((d) => (
          <li key={d.source}>
            <label>
              <input
                type="checkbox"
                checked={selected.includes(d.source)}
                onChange={() => toggle(d.source)}
              />
              <span title={d.source}>{d.source}</span> <small>({d.chunks})</small>
            </label>
            <button
              aria-label={`Delete ${d.source}`}
              onClick={() => void run(() => deleteDocument(d.source))}
            >
              ✕
            </button>
          </li>
        ))}
        {docs.length === 0 && <li className="empty">No documents yet.</li>}
      </ul>
    </aside>
  );
}
