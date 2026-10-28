export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface Source {
  source: string;
  text: string;
  distance: number;
}

export interface DocumentInfo {
  source: string;
  chunks: number;
}

export type ChatEvent =
  | { type: "sources"; sources: Source[] }
  | { type: "token"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

async function ensureOk(res: Response): Promise<Response> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res;
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  return (await ensureOk(await fetch("/api/documents"))).json();
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData();
  form.append("file", file);
  const res = await ensureOk(await fetch("/api/documents", { method: "POST", body: form }));
  return res.json();
}

export async function deleteDocument(source: string): Promise<void> {
  await ensureOk(await fetch(`/api/documents/${encodeURIComponent(source)}`, { method: "DELETE" }));
}

/** Parse a server-sent-event text buffer into events; returns the unconsumed remainder. */
export function parseSSE(buffer: string): { events: ChatEvent[]; rest: string } {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  const events = parts
    .filter((p) => p.startsWith("data: "))
    .map((p) => JSON.parse(p.slice(6)) as ChatEvent);
  return { events, rest };
}

export async function streamChat(
  question: string,
  history: Message[],
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await ensureOk(
    await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history }),
      signal,
    }),
  );
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSSE(buffer);
    buffer = parsed.rest;
    parsed.events.forEach(onEvent);
  }
}
