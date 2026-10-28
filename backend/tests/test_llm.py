from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

from app.config import Settings
from app.llm import ClaudeLLM, GeminiLLM, build_llm

MESSAGES = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]


def test_build_llm_selects_provider() -> None:
    claude = build_llm(Settings(llm_provider="anthropic", anthropic_api_key="k"))
    gemini = build_llm(Settings(llm_provider="gemini", gemini_api_key="k"))
    assert isinstance(claude, ClaudeLLM)
    assert isinstance(gemini, GeminiLLM)


def test_llm_configured_follows_provider() -> None:
    assert not Settings(llm_provider="gemini", anthropic_api_key="k").llm_configured
    assert Settings(llm_provider="gemini", gemini_api_key="k").llm_configured
    assert Settings(llm_provider="anthropic", anthropic_api_key="k").llm_configured
    assert not Settings(_env_file=None).llm_configured


def test_gemini_maps_roles() -> None:
    llm = GeminiLLM("k", "m", 10)
    contents, config = llm._args("sys", MESSAGES)
    assert [c.role for c in contents] == ["user", "model"]
    assert config.system_instruction == "sys"
    assert config.max_output_tokens == 10


async def test_claude_complete_joins_text_blocks() -> None:
    seen: dict[str, Any] = {}

    async def create(**kwargs: Any) -> SimpleNamespace:
        seen.update(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="Hel"),
                SimpleNamespace(type="tool_use", text="ignored"),
                SimpleNamespace(type="text", text="lo"),
            ]
        )

    llm = ClaudeLLM("k", "model-x", 50)
    llm._client = SimpleNamespace(messages=SimpleNamespace(create=create))  # type: ignore[assignment]
    assert await llm.complete("sys", MESSAGES) == "Hello"
    assert seen["model"] == "model-x"
    assert seen["system"] == "sys"
    assert seen["max_tokens"] == 50


async def test_claude_stream_yields_text() -> None:
    class Stream:
        async def __aenter__(self) -> "Stream":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        @property
        def text_stream(self) -> AsyncIterator[str]:
            async def gen() -> AsyncIterator[str]:
                for t in ["a", "b"]:
                    yield t

            return gen()

    llm = ClaudeLLM("k", "m", 5)
    llm._client = SimpleNamespace(  # type: ignore[assignment]
        messages=SimpleNamespace(stream=lambda **kw: Stream())
    )
    assert [t async for t in llm.stream("s", MESSAGES)] == ["a", "b"]


async def test_gemini_complete_and_stream() -> None:
    async def generate_content(**kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(text="answer")

    async def generate_content_stream(**kwargs: Any) -> AsyncIterator[SimpleNamespace]:
        async def gen() -> AsyncIterator[SimpleNamespace]:
            for t in ["x", None, "y"]:
                yield SimpleNamespace(text=t)

        return gen()

    llm = GeminiLLM("k", "m", 5)
    models = SimpleNamespace(
        generate_content=generate_content, generate_content_stream=generate_content_stream
    )
    llm._client = SimpleNamespace(aio=SimpleNamespace(models=models))  # type: ignore[assignment]
    assert await llm.complete("s", MESSAGES) == "answer"
    assert [t async for t in llm.stream("s", MESSAGES)] == ["x", "y"]
