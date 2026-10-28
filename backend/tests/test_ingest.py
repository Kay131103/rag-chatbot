import io

import pytest
from pypdf import PdfWriter

from app.ingest import UnsupportedFileError, chunk_text, extract_text


def test_chunk_text_overlaps_and_covers() -> None:
    text = " ".join(f"word{i}" for i in range(300))
    chunks = chunk_text(text, 200, 40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    assert chunks[0].startswith("word0")
    assert chunks[-1].endswith("word299")


def test_chunk_text_short_text_is_single_chunk() -> None:
    assert chunk_text("  short text  ", 100, 10) == ["short text"]


def test_chunk_text_prefers_paragraph_boundary() -> None:
    text = "a" * 60 + "\n\n" + "b" * 60
    chunks = chunk_text(text, 100, 0)
    assert chunks[0] == "a" * 60


def test_chunk_text_consecutive_chunks_overlap() -> None:
    text = "".join(str(i % 10) for i in range(500))
    chunks = chunk_text(text, 100, 20)
    assert chunks[0][-20:] == chunks[1][:20]


def test_chunk_text_empty() -> None:
    assert chunk_text("   ", 100, 10) == []


def test_chunk_text_invalid_args() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", 0, 0)
    with pytest.raises(ValueError):
        chunk_text("abc", 10, 10)
    with pytest.raises(ValueError):
        chunk_text("abc", 10, -1)


def test_extract_text_plain() -> None:
    assert extract_text("a.md", b"# hi") == "# hi"
    assert extract_text("A.TXT", b"upper") == "upper"


def test_extract_text_replaces_invalid_utf8() -> None:
    assert extract_text("a.txt", b"ok\xff") == "ok�"


def test_extract_text_pdf() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    assert extract_text("blank.pdf", buf.getvalue()).strip() == ""


def test_extract_text_unsupported() -> None:
    with pytest.raises(UnsupportedFileError):
        extract_text("a.exe", b"")
