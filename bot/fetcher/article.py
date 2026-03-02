"""Generic article fetcher using httpx + BeautifulSoup4. Falls back to Playwright."""

from __future__ import annotations

from dataclasses import dataclass


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
    # TODO: implement httpx + BS4 with Playwright fallback
    raise NotImplementedError("Article fetcher not yet implemented")
