"""X.com content fetcher using twikit. Handles tweets and X Articles."""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field

from loguru import logger
from twikit import Client

_COOKIES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "cookies.json")
_COOKIES_PATH = os.path.normpath(_COOKIES_PATH)

_client: Client | None = None
_client_lock = asyncio.Lock()


@dataclass
class TweetContent:
    tweet_id: str
    author_name: str
    author_username: str
    follower_count: int
    is_verified: bool
    text: str
    embedded_urls: list[str] = field(default_factory=list)


@dataclass
class ArticleContent:
    url: str
    title: str | None
    author_name: str | None
    body: str


_TWEET_URL_RE = re.compile(r"x\.com/\w+/status/(\d+)")
_ARTICLE_URL_RE = re.compile(r"x\.com/i/article/")
_URL_RE = re.compile(r"https?://\S+")


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


async def _get_client(username: str, email: str, password: str) -> Client:
    """Return authenticated twikit client, reusing existing session via cookies."""
    global _client
    async with _client_lock:
        if _client is not None:
            return _client

        client = Client(language="en-US")

        if os.path.exists(_COOKIES_PATH):
            logger.info("Loading twikit session from cookies.json")
            client.load_cookies(_COOKIES_PATH)
        else:
            logger.info("Logging in to X.com via twikit")
            await client.login(
                auth_info_1=username,
                auth_info_2=email,
                password=password,
            )
            client.save_cookies(_COOKIES_PATH)
            logger.info("twikit session saved to cookies.json")

        _client = client
        return _client


async def fetch_tweet(
    tweet_id: str,
    username: str | None,
    email: str | None,
    password: str | None,
) -> TweetContent:
    """Fetch tweet content via twikit."""
    if not (username and email and password):
        raise RuntimeError("Twitter credentials not configured — set TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_EMAIL")
    client = await _get_client(username, email, password)
    tweet = await client.get_tweet_by_id(tweet_id)

    text = tweet.full_text or tweet.text or ""
    embedded_urls = _URL_RE.findall(text)

    return TweetContent(
        tweet_id=tweet_id,
        author_name=tweet.user.name,
        author_username=tweet.user.screen_name,
        follower_count=tweet.user.followers_count or 0,
        is_verified=bool(tweet.user.verified),
        text=text,
        embedded_urls=embedded_urls,
    )


async def fetch_article(url: str) -> ArticleContent:
    """Fetch X Article via Playwright (JS-rendered, no twikit support)."""
    from bot.fetcher.playwright import fetch_with_playwright

    page = await fetch_with_playwright(url)
    return ArticleContent(
        url=url,
        title=page.title,
        author_name=None,
        body=page.body,
    )
