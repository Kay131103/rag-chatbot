import {
  addUrl,
  deleteDocument,
  getHealth,
  listDocuments,
  parseSSE,
  streamChat,
  uploadDocument,
  type ChatEvent,
} from "./api";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

function sseResponse(chunks: string[]) {
  const enc = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      chunks.forEach((c) => controller.enqueue(enc.encode(c)));
      controller.close();
    },
  });
  return new Response(stream, { status: 200 });
}

afterEach(() => vi.unstubAllGlobals());

describe("parseSSE", () => {
  it("parses complete events and keeps the remainder", () => {
    const { events, rest } = parseSSE(
      'data: {"type":"token","text":"Hi"}\n\ndata: {"type":"done"}\n\ndata: {"typ',
    );
    expect(events).toEqual([{ type: "token", text: "Hi" }, { type: "done" }]);
    expect(rest).toBe('data: {"typ');
  });

  it("ignores non-data lines and returns empty on blank input", () => {
    expect(parseSSE(": keep-alive\n\n").events).toEqual([]);
    expect(parseSSE("")).toEqual({ events: [], rest: "" });
  });
});

describe("REST helpers", () => {
  it("listDocuments returns parsed JSON", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json([{ source: "a", chunks: 1 }])));
    expect(await listDocuments()).toEqual([{ source: "a", chunks: 1 }]);
  });

  it("surfaces the server's error detail", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json({ detail: "nope" }, 415)));
    await expect(listDocuments()).rejects.toThrow("nope");
  });

  it("falls back to a status message when the error body is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("oops", { status: 500 })));
    await expect(getHealth()).rejects.toThrow("Request failed (500)");
  });

  it("uploadDocument posts multipart form data", async () => {
    const fetchMock = vi.fn(async () => json({ source: "a.txt", chunks: 1 }));
    vi.stubGlobal("fetch", fetchMock);
    await uploadDocument(new File(["x"], "a.txt"));
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/documents");
    expect(init.method).toBe("POST");
    expect((init.body as FormData).get("file")).toBeInstanceOf(File);
  });

  it("addUrl posts the url as JSON", async () => {
    const fetchMock = vi.fn(async () => json({ source: "u", chunks: 2 }));
    vi.stubGlobal("fetch", fetchMock);
    await addUrl("https://example.com");
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/documents/url");
    expect(JSON.parse(init.body as string)).toEqual({ url: "https://example.com" });
  });

  it("deleteDocument encodes each path segment but keeps slashes", async () => {
    const fetchMock = vi.fn(async () => json({}));
    vi.stubGlobal("fetch", fetchMock);
    await deleteDocument("https://x.com/a b");
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/documents/https%3A//x.com/a%20b");
    expect(init.method).toBe("DELETE");
  });
});

describe("streamChat", () => {
  it("emits events even when they are split across chunks", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        sseResponse(['data: {"type":"tok', 'en","text":"Hi"}\n\n', 'data: {"type":"done"}\n\n']),
      ),
    );
    const events: ChatEvent[] = [];
    await streamChat("q", [], ["a.txt"], (e) => events.push(e));
    expect(events).toEqual([{ type: "token", text: "Hi" }, { type: "done" }]);
  });

  it("sends question, history and source filter", async () => {
    const fetchMock = vi.fn(async () => sseResponse([]));
    vi.stubGlobal("fetch", fetchMock);
    await streamChat("q", [{ role: "user", content: "h" }], ["a"], () => {});
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({
      question: "q",
      history: [{ role: "user", content: "h" }],
      sources: ["a"],
    });
  });
});
