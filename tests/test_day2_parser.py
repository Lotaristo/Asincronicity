from __future__ import annotations

from aiohttp import web

from async_crawler import AsyncCrawler, HTMLParser


VALID_HTML = """
<html>
  <head>
    <title>Example Page</title>
    <meta name="description" content="Example description">
    <meta name="keywords" content="async,crawler">
  </head>
  <body>
    <h1>Main Heading</h1>
    <h2>Sub Heading</h2>
    <p class="content">Hello <strong>crawler</strong></p>
    <a href="/about">About</a>
    <a href="https://external.example/news#section">News</a>
    <a href="mailto:test@example.com">Email</a>
    <img src="/logo.png" alt="Logo">
    <table>
      <tr><th>Name</th><th>Value</th></tr>
      <tr><td>A</td><td>1</td></tr>
    </table>
    <ul><li>First</li><li>Second</li></ul>
  </body>
</html>
"""


async def test_parse_valid_html_extracts_structured_data():
    parser = HTMLParser()

    result = await parser.parse_html(VALID_HTML, "https://example.com/index.html")

    assert result["url"] == "https://example.com/index.html"
    assert result["title"] == "Example Page"
    assert result["metadata"] == {
        "title": "Example Page",
        "description": "Example description",
        "keywords": "async,crawler",
    }
    assert "Hello crawler" in result["text"]
    assert result["links"] == [
        "https://example.com/about",
        "https://external.example/news",
    ]
    assert result["images"] == [{"src": "https://example.com/logo.png", "alt": "Logo"}]
    assert result["headings"] == [
        {"level": "h1", "text": "Main Heading"},
        {"level": "h2", "text": "Sub Heading"},
    ]
    assert result["tables"] == [[["Name", "Value"], ["A", "1"]]]
    assert result["lists"] == [{"type": "ul", "items": ["First", "Second"]}]


async def test_broken_html_returns_partial_results():
    parser = HTMLParser()

    result = await parser.parse_html("<html><title>Broken<body><h1>Still works", "https://example.com")

    assert result["url"] == "https://example.com"
    assert result["title"]
    assert result["text"]


async def test_parse_html_keeps_partial_results_when_extractor_fails(monkeypatch, caplog):
    parser = HTMLParser()

    def raise_text_error(*args, **kwargs):
        raise RuntimeError("text failed")

    monkeypatch.setattr(parser, "extract_text", raise_text_error)

    result = await parser.parse_html(VALID_HTML, "https://example.com/index.html")

    assert result["title"] == "Example Page"
    assert result["text"] == ""
    assert result["links"] == [
        "https://example.com/about",
        "https://external.example/news",
    ]
    assert "text extraction failed" in caplog.text


async def test_extract_text_with_selector():
    parser = HTMLParser()

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(VALID_HTML, "lxml")
    assert parser.extract_text(soup, ".content") == "Hello crawler"


async def test_fetch_and_parse_integrates_crawler_and_parser(aiohttp_client):
    async def handler(request):
        return web.Response(text=VALID_HTML, content_type="text/html")

    app = web.Application()
    app.router.add_get("/page", handler)
    client = await aiohttp_client(app)

    crawler = AsyncCrawler(max_concurrent=2)
    try:
        result = await crawler.fetch_and_parse(str(client.make_url("/page")))
    finally:
        await crawler.close()

    assert result["title"] == "Example Page"
    assert result["links"][0] == str(client.make_url("/about"))
    assert len(result["images"]) == 1
