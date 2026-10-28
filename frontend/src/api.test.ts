import { parseSSE } from "./api";

describe("parseSSE", () => {
  it("parses complete events and keeps the remainder", () => {
    const { events, rest } = parseSSE(
      'data: {"type":"token","text":"Hi"}\n\ndata: {"type":"done"}\n\ndata: {"typ',
    );
    expect(events).toEqual([{ type: "token", text: "Hi" }, { type: "done" }]);
    expect(rest).toBe('data: {"typ');
  });
});
