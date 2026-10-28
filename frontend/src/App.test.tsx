import { render, screen } from "@testing-library/react";
import App from "./App";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response("[]", { status: 200 })),
  );
});

it("renders the panel and chat input", async () => {
  render(<App />);
  expect(screen.getByText("Knowledge base")).toBeInTheDocument();
  expect(screen.getByLabelText("Question")).toBeInTheDocument();
  expect(await screen.findByText("No documents yet.")).toBeInTheDocument();
});
