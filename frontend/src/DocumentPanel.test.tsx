import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import * as api from "./api";
import DocumentPanel from "./DocumentPanel";

afterEach(() => vi.restoreAllMocks());

const DOCS = [
  { source: "a.txt", chunks: 2 },
  { source: "b.md", chunks: 5 },
];

it("lists documents with chunk counts", async () => {
  vi.spyOn(api, "listDocuments").mockResolvedValue(DOCS);
  render(<DocumentPanel selected={[]} onSelectedChange={() => {}} />);
  expect(await screen.findByText("a.txt")).toBeInTheDocument();
  expect(screen.getByText("(5)")).toBeInTheDocument();
  expect(screen.getByText(/Searching all documents/)).toBeInTheDocument();
});

it("reports selection changes", async () => {
  vi.spyOn(api, "listDocuments").mockResolvedValue(DOCS);
  const onChange = vi.fn();
  render(<DocumentPanel selected={["a.txt"]} onSelectedChange={onChange} />);
  const boxes = await screen.findAllByRole("checkbox");
  fireEvent.click(boxes[1]);
  expect(onChange).toHaveBeenLastCalledWith(["a.txt", "b.md"]);
  fireEvent.click(boxes[0]);
  expect(onChange).toHaveBeenLastCalledWith([]);
});

it("drops selections for documents that no longer exist", async () => {
  vi.spyOn(api, "listDocuments").mockResolvedValue(DOCS);
  const onChange = vi.fn();
  render(<DocumentPanel selected={["gone.txt", "a.txt"]} onSelectedChange={onChange} />);
  await waitFor(() => expect(onChange).toHaveBeenCalledWith(["a.txt"]));
});

it("uploads chosen files and refreshes", async () => {
  const list = vi.spyOn(api, "listDocuments").mockResolvedValue([]);
  const upload = vi.spyOn(api, "uploadDocument").mockResolvedValue(DOCS[0]);
  const { container } = render(<DocumentPanel selected={[]} onSelectedChange={() => {}} />);
  await screen.findByText("No documents yet.");
  const file = new File(["hi"], "a.txt", { type: "text/plain" });
  fireEvent.change(container.querySelector('input[type="file"]')!, { target: { files: [file] } });
  await waitFor(() => expect(upload).toHaveBeenCalledWith(file, 0, expect.anything()));
  await waitFor(() => expect(list).toHaveBeenCalledTimes(2));
});

it("shows upload errors", async () => {
  vi.spyOn(api, "listDocuments").mockResolvedValue([]);
  vi.spyOn(api, "uploadDocument").mockRejectedValue(new Error("Unsupported file type"));
  const { container } = render(<DocumentPanel selected={[]} onSelectedChange={() => {}} />);
  await screen.findByText("No documents yet.");
  const file = new File(["x"], "a.exe");
  fireEvent.change(container.querySelector('input[type="file"]')!, { target: { files: [file] } });
  expect(await screen.findByText("Unsupported file type")).toBeInTheDocument();
});

it("adds a URL and clears the input", async () => {
  vi.spyOn(api, "listDocuments").mockResolvedValue([]);
  const add = vi.spyOn(api, "addUrl").mockResolvedValue(DOCS[0]);
  render(<DocumentPanel selected={[]} onSelectedChange={() => {}} />);
  const input = screen.getByLabelText("Page URL");
  expect(screen.getByText("Add")).toBeDisabled();
  fireEvent.change(input, { target: { value: " https://example.com " } });
  fireEvent.click(screen.getByText("Add"));
  await waitFor(() => expect(add).toHaveBeenCalledWith("https://example.com"));
  expect(input).toHaveValue("");
});

it("deletes a document", async () => {
  vi.spyOn(api, "listDocuments").mockResolvedValue(DOCS);
  const del = vi.spyOn(api, "deleteDocument").mockResolvedValue();
  render(<DocumentPanel selected={[]} onSelectedChange={() => {}} />);
  fireEvent.click(await screen.findByLabelText("Delete a.txt"));
  await waitFor(() => expect(del).toHaveBeenCalledWith("a.txt"));
});
