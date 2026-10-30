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

// Same origin by default (Vite dev proxy). Point this at your deployed backend
// (e.g. VITE_API_URL=https://api.example.com) when the frontend is hosted separately.
const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "";
const API_KEY = (import.meta.env.VITE_API_KEY as string | undefined) ?? "";

function apiPath(path: string): string {
  return `${BASE_URL}${path}`;
}

function withKey(headers: Headers): Headers {
  if (API_KEY) headers.set("X-API-Key", API_KEY);
  return headers;
}

async function ensureOk(res: Response): Promise<Response> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res;
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await ensureOk(await fetch(apiPath("/api/documents"), { headers: withKey(new Headers()) }));
  return res.json();
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData();
  form.append("file", file);
  const res = await ensureOk(
    await fetch(apiPath("/api/documents"), {
      method: "POST",
      body: form,
      headers: withKey(new Headers()),
    }),
  );
  return res.json();
}

export async function addUrl(url: string): Promise<DocumentInfo> {
  const res = await ensureOk(
    await fetch(apiPath("/api/documents/url"), {
      method: "POST",
      headers: withKey(new Headers({ "Content-Type": "application/json" })),
      body: JSON.stringify({ url }),
    }),
  );
  return res.json();
}

export async function getHealth(): Promise<{ status: string; llm_configured: boolean }> {
  const res = await ensureOk(await fetch(apiPath("/api/health"), { headers: withKey(new Headers()) }));
  return res.json();
}

export async function deleteDocument(source: string): Promise<void> {
  const path = source.split("/").map(encodeURIComponent).join("/");
  await ensureOk(
    await fetch(apiPath(`/api/documents/${path}`), { method: "DELETE", headers: withKey(new Headers()) }),
  );
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
  sources: string[],
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await ensureOk(
    await fetch(apiPath("/api/chat"), {
      method: "POST",
      headers: withKey(new Headers({ "Content-Type": "application/json" })),
      body: JSON.stringify({ question, history, sources }),
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
