"""Tests for GitHub URL extraction from fetched content."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, patch

import pytest

from bot.analyzer.extractor import extract_github_urls
from bot.fetcher.github import RepoContent


@dataclass
class FakeArticle:
    title: str = ""
    body: str = ""


@dataclass
class FakeTweet:
    text: str = ""
    embedded_urls: list[str] = field(default_factory=list)


class TestExtractGithubUrls:
    @pytest.mark.asyncio()
    async def test_article_with_two_repos(self) -> None:
        article = FakeArticle(body="Check out https://github.com/owner/repo-one and https://github.com/owner/repo-two")
        result = await extract_github_urls(article, "https://example.com/article")
        assert result == [
            "https://github.com/owner/repo-one",
            "https://github.com/owner/repo-two",
        ]

    @pytest.mark.asyncio()
    async def test_tweet_embedded_github_url(self) -> None:
        tweet = FakeTweet(
            text="Great tool!",
            embedded_urls=["https://github.com/user/cool-lib"],
        )
        result = await extract_github_urls(tweet, "https://x.com/user/status/123")
        assert result == ["https://github.com/user/cool-lib"]

    @pytest.mark.asyncio()
    async def test_tweet_text_body(self) -> None:
        tweet = FakeTweet(text="Try https://github.com/user/my-tool for automation")
        result = await extract_github_urls(tweet, "https://x.com/user/status/123")
        assert result == ["https://github.com/user/my-tool"]

    @pytest.mark.asyncio()
    async def test_repo_content_returns_empty(self) -> None:
        repo = RepoContent(
            owner="owner",
            repo="repo",
            description="desc",
            stars=100,
            language="Python",
            readme="See also https://github.com/other/repo",
        )
        result = await extract_github_urls(repo, "https://github.com/owner/repo")
        assert result == []

    @pytest.mark.asyncio()
    async def test_source_url_filtered_out(self) -> None:
        article = FakeArticle(body="About https://github.com/owner/self-repo and https://github.com/owner/other-repo")
        result = await extract_github_urls(article, "https://github.com/owner/self-repo")
        assert result == ["https://github.com/owner/other-repo"]

    @pytest.mark.asyncio()
    async def test_duplicates_removed(self) -> None:
        article = FakeArticle(body="https://github.com/owner/repo https://github.com/owner/repo again")
        result = await extract_github_urls(article, "https://example.com")
        assert result == ["https://github.com/owner/repo"]

    @pytest.mark.asyncio()
    async def test_max_cap(self) -> None:
        urls = " ".join(f"https://github.com/owner/repo-{i}" for i in range(10))
        article = FakeArticle(body=urls)
        result = await extract_github_urls(article, "https://example.com")
        assert len(result) == 5

    @pytest.mark.asyncio()
    async def test_non_repo_urls_filtered(self) -> None:
        article = FakeArticle(body="Visit https://github.com/settings or https://github.com/owner/real-repo")
        result = await extract_github_urls(article, "https://example.com")
        assert result == ["https://github.com/owner/real-repo"]

    @pytest.mark.asyncio()
    async def test_url_with_trailing_path(self) -> None:
        article = FakeArticle(body="See https://github.com/owner/repo/tree/main/src for details")
        result = await extract_github_urls(article, "https://example.com")
        assert result == ["https://github.com/owner/repo"]

    @pytest.mark.asyncio()
    async def test_empty_content(self) -> None:
        article = FakeArticle(body="No links here")
        result = await extract_github_urls(article, "https://example.com")
        assert result == []

    @pytest.mark.asyncio()
    async def test_tco_shortlink_resolved(self) -> None:
        """t.co links in embedded_urls are resolved to final GitHub URLs."""
        tweet = FakeTweet(
            text="GitHub Repository:",
            embedded_urls=["https://t.co/FApE40Q0uh"],
        )

        mock_response = AsyncMock()
        mock_response.url = "https://github.com/VoltAgent/awesome-design-md"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.head = AsyncMock(return_value=mock_response)

        with patch("bot.analyzer.extractor.httpx.AsyncClient", return_value=mock_client):
            result = await extract_github_urls(tweet, "https://x.com/user/status/123")

        assert result == ["https://github.com/VoltAgent/awesome-design-md"]

    @pytest.mark.asyncio()
    async def test_tco_resolution_failure_skips(self) -> None:
        """If t.co resolution fails, the shortlink is kept (and filtered as non-GitHub)."""
        tweet = FakeTweet(
            text="Check this:",
            embedded_urls=["https://t.co/broken"],
        )

        with patch("bot.analyzer.extractor.httpx.AsyncClient", side_effect=Exception("network error")):
            result = await extract_github_urls(tweet, "https://x.com/user/status/123")

        # t.co URL doesn't match GitHub pattern, so filtered out
        assert result == []
