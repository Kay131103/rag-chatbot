import asyncio
import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

MAX_BYTES = 5_000_000
_SKIP = {"script", "style", "noscript", "svg", "head"}


class FetchError(ValueError):
    """Raised when a URL cannot be safely fetched."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP and self._skip:
            self._skip -= 1
        elif tag in {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.parts.append(data.strip() + " ")


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    lines = (line.strip() for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


async def _check_public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise FetchError("Only http(s) URLs are supported")
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise FetchError(f"Cannot resolve host: {parsed.hostname}") from e
    for info in infos:
        if not ipaddress.ip_address(str(info[4][0])).is_global:
            raise FetchError("URL resolves to a non-public address")


async def fetch_page_text(url: str) -> str:
    """Download a public web page (or text file) and return its readable text."""
    await _check_public_host(url)
    try:
        async with (
            httpx.AsyncClient(timeout=15, follow_redirects=False) as client,
            client.stream("GET", url) as resp,
        ):
            if resp.status_code >= 400:
                raise FetchError(f"URL returned HTTP {resp.status_code}")
            body = b""
            async for part in resp.aiter_bytes():
                body += part
                if len(body) > MAX_BYTES:
                    raise FetchError("Page is too large")
            ctype = resp.headers.get("content-type", "")
    except httpx.HTTPError as e:
        raise FetchError(f"Request failed: {e}") from e
    text = body.decode("utf-8", errors="replace")
    return html_to_text(text) if "html" in ctype else text
