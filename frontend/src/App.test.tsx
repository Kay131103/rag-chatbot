import { fireEvent, render, screen } from "@testing-library/react";
import App from "./App";

function mockFetch(routes: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => new Response(JSON.stringify(routes[url] ?? []), { status: 200 })),
  );
}

beforeEach(() => {
  localStorage.clear();
  mockFetch({ "/api/health": { status: "ok", llm_configured: true } });
});

it("renders the panel and chat input", async () => {
  render(<App />);
  expect(screen.getByText("Knowledge base")).toBeInTheDocument();
  expect(screen.getByLabelText("Question")).toBeInTheDocument();
  expect(await screen.findByText("No documents yet.")).toBeInTheDocument();
});

it("warns when the LLM is not configured", async () => {
  mockFetch({ "/api/health": { status: "ok", llm_configured: false } });
  render(<App />);
  expect(await screen.findByText(/the LLM API key is not set/)).toBeInTheDocument();
});

it("lists documents and toggles the source filter", async () => {
  mockFetch({
    "/api/health": { status: "ok", llm_configured: true },
    "/api/documents": [{ source: "a.txt", chunks: 2 }],
  });
  render(<App />);
  const box = await screen.findByRole("checkbox");
  fireEvent.click(box);
  expect(await screen.findByText("Searching 1 selected.")).toBeInTheDocument();
});

it("restores the conversation from localStorage", () => {
  localStorage.setItem(
    "rag-chat-turns",
    JSON.stringify([
      { role: "user", content: "hello?" },
      { role: "assistant", content: "**hi**" },
    ]),
  );
  render(<App />);
  expect(screen.getByText("hello?")).toBeInTheDocument();
  expect(screen.getByText("hi").tagName).toBe("STRONG");
});
