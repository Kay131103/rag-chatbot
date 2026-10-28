from collections.abc import AsyncIterator
from typing import Protocol

from anthropic import AsyncAnthropic
from google import genai
from google.genai import types

from app.config import Settings


class LLM(Protocol):
    async def complete(self, system: str, messages: list[dict[str, str]]) -> str: ...

    def stream(self, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]: ...


class ClaudeLLM:
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=messages,  # type: ignore[arg-type]
        )
        return "".join(b.text for b in resp.content if b.type == "text")

    async def stream(self, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=messages,  # type: ignore[arg-type]
        ) as s:
            async for text in s.text_stream:
                yield text


class GeminiLLM:
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def _args(
        self, system: str, messages: list[dict[str, str]]
    ) -> tuple[list[types.Content], types.GenerateContentConfig]:
        contents = [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part(text=m["content"])],
            )
            for m in messages
        ]
        config = types.GenerateContentConfig(
            system_instruction=system, max_output_tokens=self._max_tokens
        )
        return contents, config

    async def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        contents, config = self._args(system, messages)
        resp = await self._client.aio.models.generate_content(
            model=self._model, contents=contents, config=config
        )
        return resp.text or ""

    async def stream(self, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        contents, config = self._args(system, messages)
        stream = await self._client.aio.models.generate_content_stream(
            model=self._model, contents=contents, config=config
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text


def build_llm(settings: Settings) -> LLM:
    if settings.llm_provider == "gemini":
        return GeminiLLM(settings.gemini_api_key, settings.gemini_model, settings.max_tokens)
    return ClaudeLLM(settings.anthropic_api_key, settings.claude_model, settings.max_tokens)
