import pytest

from app.web import FetchError, fetch_page_text, html_to_text


def test_html_to_text_strips_scripts() -> None:
    html = (
        "<html><head><title>x</title></head>"
        "<body><script>bad()</script><h1>Hi</h1><p>There</p></body></html>"
    )
    assert html_to_text(html) == "Hi\nThere"


@pytest.mark.parametrize(
    "url",
    ["ftp://example.com/a", "http://127.0.0.1/", "http://localhost:8000/x", "http://10.0.0.1/"],
)
async def test_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(FetchError):
        await fetch_page_text(url)
