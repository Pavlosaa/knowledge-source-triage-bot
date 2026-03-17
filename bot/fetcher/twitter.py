"""X.com content fetcher using ScrapFly API. Handles tweets and X Articles."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup
from loguru import logger

_SCRAPFLY_API = "https://api.scrapfly.io/scrape"
_SCRAPFLY_TIMEOUT = 160.0  # ScrapFly default read timeout is 155s


class ScrapFlyError(Exception):
    """Raised when ScrapFly API call fails."""


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


_TWEET_URL_RE = re.compile(r"x\.com/(\w+)/status/(\d+)")
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
    return match.group(2) if match else None


def _extract_author_username(url: str) -> str:
    """Extract author username from tweet URL."""
    match = _TWEET_URL_RE.search(url)
    return match.group(1) if match else "unknown"


async def _scrapfly_fetch(url: str, api_key: str) -> str:
    """Call ScrapFly API and return rendered HTML."""
    params = {
        "url": url,
        "key": api_key,
        "asp": "true",
        "render_js": "true",
        "country": "us",
    }
    async with httpx.AsyncClient(timeout=_SCRAPFLY_TIMEOUT) as client:
        response = await client.get(_SCRAPFLY_API, params=params)

    if response.status_code != 200:
        raise ScrapFlyError(f"ScrapFly returned {response.status_code}: {response.text[:200]}")

    data = response.json()
    result = data.get("result", {})
    html: str = result.get("content", "")
    if not html:
        raise ScrapFlyError("ScrapFly returned empty content")

    return html


def _parse_tweet_html(html: str, tweet_id: str, url: str) -> TweetContent:
    """Parse rendered tweet page HTML into TweetContent."""
    soup = BeautifulSoup(html, "lxml")
    author_username = _extract_author_username(url)

    # Primary: data-testid selectors
    tweet_text_el = soup.select_one('[data-testid="tweetText"]')
    text = tweet_text_el.get_text(separator=" ", strip=True) if tweet_text_el else ""

    # Author display name from User-Name testid
    user_name_el = soup.select_one('[data-testid="User-Name"]')
    author_name = user_name_el.get_text(separator=" ", strip=True) if user_name_el else ""
    # Clean up: User-Name often contains both display name and @handle
    if author_name and f"@{author_username}" in author_name:
        author_name = author_name.split(f"@{author_username}")[0].strip()

    # Fallback: extract from <article> elements
    if not text:
        logger.warning("Primary tweet selectors failed, falling back to <article>")
        articles = soup.find_all("article")
        texts = [a.get_text(separator=" ", strip=True) for a in articles]
        text = " ".join(texts)

    if not author_name:
        author_name = author_username

    embedded_urls = _URL_RE.findall(text)

    return TweetContent(
        tweet_id=tweet_id,
        author_name=author_name,
        author_username=author_username,
        follower_count=0,
        is_verified=False,
        text=text,
        embedded_urls=embedded_urls,
    )


async def fetch_tweet(tweet_id: str, api_key: str) -> TweetContent:
    """Fetch tweet content via ScrapFly API."""
    url = f"https://x.com/i/status/{tweet_id}"
    logger.info(f"Fetching tweet {tweet_id} via ScrapFly")

    html = await _scrapfly_fetch(url, api_key)
    return _parse_tweet_html(html, tweet_id, url)


async def fetch_article(url: str, api_key: str) -> ArticleContent:
    """Fetch X Article via ScrapFly API."""
    logger.info(f"Fetching X article via ScrapFly: {url}")

    html = await _scrapfly_fetch(url, api_key)
    soup = BeautifulSoup(html, "lxml")

    # Title from og:title or <title>
    og_title = soup.find("meta", property="og:title")
    title: str | None = None
    if og_title and hasattr(og_title, "get") and og_title.get("content"):  # type: ignore[union-attr]
        title = str(og_title["content"])  # type: ignore[index]
    if not title:
        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else None

    # Body from article or main content
    article_el = soup.find("article")
    if article_el:
        body = article_el.get_text(separator="\n", strip=True)
    else:
        main_el = soup.find("main")
        body = main_el.get_text(separator="\n", strip=True) if main_el else soup.get_text(separator="\n", strip=True)

    return ArticleContent(
        url=url,
        title=title,
        author_name=None,
        body=body,
    )
