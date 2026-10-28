import httpx
import pytest

from app import web
from app.web import FetchError, fetch_page_text, html_to_text


def _mock_client(monkeypatch: pytest.MonkeyPatch, handler: httpx.MockTransport) -> None:
    real = httpx.AsyncClient

    def factory(**kwargs: object) -> httpx.AsyncClient:
        return real(transport=handler, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def test_html_to_text_strips_scripts() -> None:
    html = (
        "<html><head><title>x</title></head>"
        "<body><script>bad()</script><h1>Hi</h1><p>There</p></body></html>"
    )
    assert html_to_text(html) == "Hi\nThere"


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/a",
        "http://127.0.0.1/",
        "http://localhost:8000/x",
        "http://10.0.0.1/",
        "http://169.254.169.254/latest/meta-data",
        "not a url",
    ],
)
async def test_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(FetchError):
        await fetch_page_text(url)


async def test_fetches_html_and_extracts_text(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "text/html"}, text="<p>Hello</p><script>x</script>"
        )

    _mock_client(monkeypatch, httpx.MockTransport(handler))
    assert await fetch_page_text("http://8.8.8.8/page") == "Hello"


async def test_plain_text_is_returned_verbatim(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = httpx.MockTransport(
        lambda r: httpx.Response(200, headers={"content-type": "text/plain"}, text="raw <b>")
    )
    _mock_client(monkeypatch, handler)
    assert await fetch_page_text("http://8.8.8.8/") == "raw <b>"


async def test_http_error_status(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_client(monkeypatch, httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(FetchError, match="404"):
        await fetch_page_text("http://8.8.8.8/missing")


async def test_oversized_page(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web, "MAX_BYTES", 10)
    _mock_client(monkeypatch, httpx.MockTransport(lambda r: httpx.Response(200, text="x" * 100)))
    with pytest.raises(FetchError, match="too large"):
        await fetch_page_text("http://8.8.8.8/big")


async def test_network_failure_is_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    _mock_client(monkeypatch, httpx.MockTransport(boom))
    with pytest.raises(FetchError, match="Request failed"):
        await fetch_page_text("http://8.8.8.8/")
