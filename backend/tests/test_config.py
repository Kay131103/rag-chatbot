import pytest

from app.config import Settings


def test_defaults() -> None:
    s = Settings(_env_file=None)
    assert s.llm_provider == "gemini"
    assert s.top_k == 4
    assert s.chunk_overlap < s.chunk_size


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("TOP_K", "9")
    s = Settings(_env_file=None)
    assert s.llm_provider == "gemini"
    assert s.top_k == 9


def test_invalid_provider_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError):
        Settings(_env_file=None)
