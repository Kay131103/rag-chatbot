import pytest

from app.ingest import UnsupportedFileError, chunk_text, extract_text


def test_chunk_text_overlaps_and_covers() -> None:
    text = " ".join(f"word{i}" for i in range(300))
    chunks = chunk_text(text, 200, 40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    assert chunks[0].startswith("word0")
    assert chunks[-1].endswith("word299")


def test_chunk_text_empty() -> None:
    assert chunk_text("   ", 100, 10) == []


def test_chunk_text_invalid_args() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", 0, 0)
    with pytest.raises(ValueError):
        chunk_text("abc", 10, 10)


def test_extract_text_plain() -> None:
    assert extract_text("a.md", b"# hi") == "# hi"


def test_extract_text_unsupported() -> None:
    with pytest.raises(UnsupportedFileError):
        extract_text("a.exe", b"")
