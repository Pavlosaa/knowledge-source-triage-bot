"""Generic article fetcher using httpx + BeautifulSoup4. Falls back to Playwright."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from loguru import logger

# Minimum content length to consider httpx fetch successful
_MIN_CONTENT_LENGTH = 200

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Semantic content selectors in priority order
_CONTENT_SELECTORS = ["article", "main", "[role=main]", ".content", "#content", "body"]


@dataclass
class ArticleContent:
    url: str
    title: str | None
    body: str


async def fetch_article(url: str) -> ArticleContent:
    """
    Fetch article content.
    Tries httpx + BS4 first; falls back to Playwright for JS-heavy pages.
    """
    logger.info(f"Fetching article: {url}")

    try:
        result = await _fetch_with_httpx(url)
        if len(result.body) >= _MIN_CONTENT_LENGTH:
            logger.info(f"httpx fetch succeeded: {len(result.body)} chars")
            return result
        logger.info(f"httpx returned too little content ({len(result.body)} chars), falling back to Playwright")
    except Exception as exc:
        logger.warning(f"httpx fetch failed for {url}: {exc}")

    return await _fetch_with_playwright_fallback(url)


async def _fetch_with_httpx(url: str) -> ArticleContent:
    async with httpx.AsyncClient(
        headers=_HEADERS,
        follow_redirects=True,
        timeout=20.0,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Remove boilerplate tags
    for tag in soup.find_all(["nav", "header", "footer", "aside", "script", "style"]):
        tag.decompose()

    body = ""
    for selector in _CONTENT_SELECTORS:
        element = soup.select_one(selector)
        if element:
            body = element.get_text(separator="\n", strip=True)
            break

    return ArticleContent(url=url, title=title, body=body)


async def _fetch_with_playwright_fallback(url: str) -> ArticleContent:
    from bot.fetcher.playwright import fetch_with_playwright

    page = await fetch_with_playwright(url)
    return ArticleContent(url=url, title=page.title, body=page.body)
