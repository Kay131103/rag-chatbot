from collections.abc import AsyncIterator
from typing import Protocol

from anthropic import AsyncAnthropic


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
