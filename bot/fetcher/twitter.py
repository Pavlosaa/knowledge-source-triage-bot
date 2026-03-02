"""X.com content fetcher using twikit. Handles tweets and X Articles."""

from __future__ import annotations

import re
from dataclasses import dataclass

# TODO: import twikit and implement session management


@dataclass
class TweetContent:
    tweet_id: str
    author_name: str
    author_username: str
    follower_count: int
    is_verified: bool
    text: str
    embedded_urls: list[str]


@dataclass
class ArticleContent:
    url: str
    title: str | None
    author_name: str | None
    body: str


_TWEET_URL_RE = re.compile(r"x\.com/\w+/status/(\d+)")
_ARTICLE_URL_RE = re.compile(r"x\.com/i/article/")


def detect_content_type(url: str) -> str:
    """Return 'tweet', 'article', or 'unknown'."""
    if _TWEET_URL_RE.search(url):
        return "tweet"
    if _ARTICLE_URL_RE.search(url):
        return "article"
    return "unknown"


def extract_tweet_id(url: str) -> str | None:
    match = _TWEET_URL_RE.search(url)
    return match.group(1) if match else None


async def fetch_tweet(tweet_id: str) -> TweetContent:
    """Fetch tweet content via twikit."""
    # TODO: implement twikit session + fetch
    raise NotImplementedError("twikit not yet implemented")


async def fetch_article(url: str) -> ArticleContent:
    """Fetch X Article via twikit (with Playwright fallback in fetcher/playwright.py)."""
    # TODO: implement
    raise NotImplementedError("X Article fetching not yet implemented")
