import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import * as api from "./api";
import Chat from "./Chat";

afterEach(() => vi.restoreAllMocks());
beforeEach(() => localStorage.clear());

function send(text: string) {
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: text } });
  fireEvent.click(screen.getByText("Send"));
}

it("disables Send until there is text", () => {
  render(<Chat sources={[]} />);
  expect(screen.getByText("Send")).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: "hi" } });
  expect(screen.getByText("Send")).toBeEnabled();
});

it("streams tokens and shows sources", async () => {
  vi.spyOn(api, "streamChat").mockImplementation(async (_q, _h, _s, onEvent) => {
    onEvent({
      type: "sources",
      sources: [{ source: "a.txt", text: "passage text", distance: 0.1 }],
    });
    onEvent({ type: "token", text: "Hello " });
    onEvent({ type: "token", text: "world" });
    onEvent({ type: "done" });
  });
  render(<Chat sources={["a.txt"]} />);
  send("What?");
  expect(await screen.findByText("Hello world")).toBeInTheDocument();
  expect(screen.getByText("What?")).toBeInTheDocument();
  expect(screen.getByText("1 sources")).toBeInTheDocument();
  expect(screen.getByText("passage text")).toBeInTheDocument();
  expect(api.streamChat).toHaveBeenCalledWith("What?", [], ["a.txt"], expect.any(Function), expect.anything());
  expect(screen.getByLabelText("Question")).toHaveValue("");
});

it("passes prior turns as history on the next question", async () => {
  const spy = vi.spyOn(api, "streamChat").mockImplementation(async (_q, _h, _s, onEvent) => {
    onEvent({ type: "token", text: "answer" });
  });
  render(<Chat sources={[]} />);
  send("first");
  await screen.findByText("answer");
  send("second");
  await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
  expect(spy.mock.calls[1][1]).toEqual([
    { role: "user", content: "first" },
    { role: "assistant", content: "answer" },
  ]);
});

it("shows request errors in the conversation", async () => {
  vi.spyOn(api, "streamChat").mockRejectedValue(new Error("boom"));
  render(<Chat sources={[]} />);
  send("x");
  expect(await screen.findByText("Error: boom")).toBeInTheDocument();
});

it("shows server-sent error events", async () => {
  vi.spyOn(api, "streamChat").mockImplementation(async (_q, _h, _s, onEvent) => {
    onEvent({ type: "error", message: "rate limited" });
  });
  render(<Chat sources={[]} />);
  send("x");
  expect(await screen.findByText(/rate limited/)).toBeInTheDocument();
});

it("New chat clears the conversation and storage", async () => {
  vi.spyOn(api, "streamChat").mockImplementation(async (_q, _h, _s, onEvent) => {
    onEvent({ type: "token", text: "answer" });
  });
  render(<Chat sources={[]} />);
  send("hello");
  await screen.findByText("answer");
  fireEvent.click(screen.getByText("New chat"));
  expect(screen.queryByText("answer")).not.toBeInTheDocument();
  expect(JSON.parse(localStorage.getItem("rag-chat-turns") ?? "null")).toEqual([]);
});

it("Regenerate re-asks the last question without duplicating turns", async () => {
  const spy = vi.spyOn(api, "streamChat").mockImplementation(async (_q, _h, _s, onEvent) => {
    onEvent({ type: "token", text: "answer" });
  });
  render(<Chat sources={[]} />);
  send("hello");
  await screen.findByText("answer");
  fireEvent.click(screen.getByText("Regenerate"));
  await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
  expect(spy.mock.calls[1][0]).toBe("hello");
  expect(spy.mock.calls[1][1]).toEqual([]);
  expect(await screen.findAllByText("hello")).toHaveLength(1);
});
