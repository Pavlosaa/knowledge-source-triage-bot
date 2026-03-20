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
    text: str
    follower_count: int | None = None  # None = not available from HTML
    is_verified: bool | None = None  # None = not available from HTML
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
    logger.info(f"ScrapFly request: url={url}")
    async with httpx.AsyncClient(timeout=_SCRAPFLY_TIMEOUT) as client:
        response = await client.get(_SCRAPFLY_API, params=params)

    logger.info(f"ScrapFly response: status={response.status_code} content_length={len(response.content)}")

    if response.status_code != 200:
        logger.error(f"ScrapFly error body: {response.text[:500]}")
        raise ScrapFlyError(f"ScrapFly returned {response.status_code}: {response.text[:200]}")

    data = response.json()
    result = data.get("result", {})

    # Log ScrapFly result metadata (everything except the HTML content itself)
    log_url = result.get("log_url")
    status = result.get("status")
    status_code = result.get("status_code")
    success = result.get("success")
    duration = result.get("duration")
    fmt = result.get("format")
    error = result.get("error")
    logger.info(
        f"ScrapFly result: status={status} success={success} "
        f"upstream_status={status_code} duration={duration} format={fmt} "
        f"log_url={log_url}"
    )
    if error:
        logger.warning(f"ScrapFly result.error: {error}")

    html: str = result.get("content", "")
    if not html:
        logger.error(f"ScrapFly returned empty content. Full result keys: {list(result.keys())}")
        raise ScrapFlyError("ScrapFly returned empty content")

    logger.debug(f"ScrapFly HTML preview (first 500 chars): {html[:500]}")
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

    tweet = TweetContent(
        tweet_id=tweet_id,
        author_name=author_name,
        author_username=author_username,
        text=text,
        embedded_urls=embedded_urls,
    )
    logger.info(
        f"Parsed tweet: author=@{author_username} ({author_name}) "
        f"text_len={len(text)} embedded_urls={len(embedded_urls)} "
        f"followers={tweet.follower_count} verified={tweet.is_verified}"
    )
    return tweet


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
