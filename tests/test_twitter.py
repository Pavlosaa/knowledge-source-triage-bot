"""Tests for bot.fetcher.twitter — ScrapFly-based X.com fetcher."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from bot.fetcher.twitter import (
    ArticleContent,
    ScrapFlyError,
    TweetContent,
    detect_content_type,
    extract_tweet_id,
    fetch_article,
    fetch_tweet,
)

# ---------------------------------------------------------------------------
# Pure function tests (no I/O)
# ---------------------------------------------------------------------------


class TestDetectContentType:
    def test_tweet_url(self) -> None:
        assert detect_content_type("https://x.com/elonmusk/status/123456") == "tweet"

    def test_article_url(self) -> None:
        assert detect_content_type("https://x.com/i/article/some-slug") == "article"

    def test_unknown_url(self) -> None:
        assert detect_content_type("https://example.com/page") == "unknown"

    def test_x_com_profile_is_unknown(self) -> None:
        assert detect_content_type("https://x.com/elonmusk") == "unknown"


class TestExtractTweetId:
    def test_valid_url(self) -> None:
        assert extract_tweet_id("https://x.com/user/status/9876543210") == "9876543210"

    def test_invalid_url(self) -> None:
        assert extract_tweet_id("https://example.com/foo") is None

    def test_url_with_query_params(self) -> None:
        assert extract_tweet_id("https://x.com/user/status/111?s=20") == "111"


# ---------------------------------------------------------------------------
# ScrapFly fetch tests (mocked HTTP)
# ---------------------------------------------------------------------------

SAMPLE_TWEET_HTML = """
<html>
<body>
<article>
  <div data-testid="User-Name">
    <span>Elon Musk</span>
    <span>@elonmusk</span>
  </div>
  <div data-testid="tweetText">
    <span>This is a test tweet with a link https://example.com/foo</span>
  </div>
</article>
</body>
</html>
"""

SAMPLE_TWEET_HTML_NO_TESTID = """
<html>
<body>
<article>
  <p>Fallback tweet content from article element</p>
</article>
</body>
</html>
"""

SAMPLE_ARTICLE_HTML = """
<html>
<head>
  <meta property="og:title" content="Test Article Title" />
  <title>Test Article Title | X</title>
</head>
<body>
<article>
  <p>This is the article body content.</p>
  <p>Second paragraph.</p>
</article>
</body>
</html>
"""


def _scrapfly_response(html: str, status_code: int = 200) -> httpx.Response:
    """Build a mock httpx.Response mimicking ScrapFly API."""
    body = json.dumps({"result": {"content": html}})
    return httpx.Response(
        status_code=status_code,
        content=body.encode(),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://api.scrapfly.io/scrape"),
    )


def _scrapfly_error_response(status_code: int = 422, message: str = "error") -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=message.encode(),
        headers={"content-type": "text/plain"},
        request=httpx.Request("GET", "https://api.scrapfly.io/scrape"),
    )


def _scrapfly_empty_response() -> httpx.Response:
    body = json.dumps({"result": {"content": ""}})
    return httpx.Response(
        status_code=200,
        content=body.encode(),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://api.scrapfly.io/scrape"),
    )


class TestFetchTweet:
    async def test_successful_fetch(self) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_scrapfly_response(SAMPLE_TWEET_HTML))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("bot.fetcher.twitter.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_tweet("123456", api_key="test-key")

        assert isinstance(result, TweetContent)
        assert result.tweet_id == "123456"
        assert "test tweet" in result.text
        assert result.embedded_urls == ["https://example.com/foo"]
        assert result.follower_count is None
        assert result.is_verified is None

    async def test_scrapfly_http_error(self) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_scrapfly_error_response(422, "bad request"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("bot.fetcher.twitter.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(ScrapFlyError, match="ScrapFly returned 422"),
        ):
            await fetch_tweet("123456", api_key="test-key")

    async def test_scrapfly_empty_content(self) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_scrapfly_empty_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("bot.fetcher.twitter.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(ScrapFlyError, match="empty content"),
        ):
            await fetch_tweet("123456", api_key="test-key")

    async def test_fallback_parsing(self) -> None:
        """When data-testid selectors are missing, falls back to <article> text."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_scrapfly_response(SAMPLE_TWEET_HTML_NO_TESTID))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("bot.fetcher.twitter.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_tweet("999", api_key="test-key")

        assert isinstance(result, TweetContent)
        assert "Fallback tweet content" in result.text

    async def test_api_key_passed_as_param(self) -> None:
        """Verify API key is passed in ScrapFly request params."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_scrapfly_response(SAMPLE_TWEET_HTML))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("bot.fetcher.twitter.httpx.AsyncClient", return_value=mock_client):
            await fetch_tweet("123", api_key="my-secret-key")

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["key"] == "my-secret-key"
        assert params["asp"] == "true"
        assert params["render_js"] == "true"


class TestFetchArticle:
    async def test_successful_fetch(self) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_scrapfly_response(SAMPLE_ARTICLE_HTML))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("bot.fetcher.twitter.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_article("https://x.com/i/article/test", api_key="test-key")

        assert isinstance(result, ArticleContent)
        assert result.title == "Test Article Title"
        assert "article body content" in result.body
        assert result.url == "https://x.com/i/article/test"

    async def test_scrapfly_error(self) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_scrapfly_error_response(500, "server error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("bot.fetcher.twitter.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(ScrapFlyError, match="ScrapFly returned 500"),
        ):
            await fetch_article("https://x.com/i/article/test", api_key="test-key")
