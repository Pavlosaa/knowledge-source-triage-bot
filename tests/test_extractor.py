"""Tests for GitHub URL extraction from fetched content."""

from __future__ import annotations

from dataclasses import dataclass, field

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
    def test_article_with_two_repos(self) -> None:
        article = FakeArticle(body="Check out https://github.com/owner/repo-one and https://github.com/owner/repo-two")
        result = extract_github_urls(article, "https://example.com/article")
        assert result == [
            "https://github.com/owner/repo-one",
            "https://github.com/owner/repo-two",
        ]

    def test_tweet_embedded_urls(self) -> None:
        tweet = FakeTweet(
            text="Great tool!",
            embedded_urls=["https://github.com/user/cool-lib"],
        )
        result = extract_github_urls(tweet, "https://x.com/user/status/123")
        assert result == ["https://github.com/user/cool-lib"]

    def test_tweet_text_body(self) -> None:
        tweet = FakeTweet(text="Try https://github.com/user/my-tool for automation")
        result = extract_github_urls(tweet, "https://x.com/user/status/123")
        assert result == ["https://github.com/user/my-tool"]

    def test_repo_content_returns_empty(self) -> None:
        repo = RepoContent(
            owner="owner",
            repo="repo",
            description="desc",
            stars=100,
            language="Python",
            readme="See also https://github.com/other/repo",
        )
        result = extract_github_urls(repo, "https://github.com/owner/repo")
        assert result == []

    def test_source_url_filtered_out(self) -> None:
        article = FakeArticle(body="About https://github.com/owner/self-repo and https://github.com/owner/other-repo")
        result = extract_github_urls(article, "https://github.com/owner/self-repo")
        assert result == ["https://github.com/owner/other-repo"]

    def test_duplicates_removed(self) -> None:
        article = FakeArticle(body="https://github.com/owner/repo https://github.com/owner/repo again")
        result = extract_github_urls(article, "https://example.com")
        assert result == ["https://github.com/owner/repo"]

    def test_max_cap(self) -> None:
        urls = " ".join(f"https://github.com/owner/repo-{i}" for i in range(10))
        article = FakeArticle(body=urls)
        result = extract_github_urls(article, "https://example.com")
        assert len(result) == 5

    def test_non_repo_urls_filtered(self) -> None:
        article = FakeArticle(body="Visit https://github.com/settings or https://github.com/owner/real-repo")
        result = extract_github_urls(article, "https://example.com")
        # "settings" is not a valid repo URL (no owner/repo pattern)
        assert result == ["https://github.com/owner/real-repo"]

    def test_url_with_trailing_path(self) -> None:
        article = FakeArticle(body="See https://github.com/owner/repo/tree/main/src for details")
        result = extract_github_urls(article, "https://example.com")
        assert result == ["https://github.com/owner/repo"]

    def test_empty_content(self) -> None:
        article = FakeArticle(body="No links here")
        result = extract_github_urls(article, "https://example.com")
        assert result == []
