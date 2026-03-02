"""Playwright headless browser fetcher. Fallback for JS-rendered pages."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PageContent:
    url: str
    title: str | None
    body: str


async def fetch_with_playwright(url: str, timeout_ms: int = 30_000) -> PageContent:
    """
    Fetch a JS-rendered page using Playwright headless Chromium.
    Extracts title and visible body text.
    """
    # TODO: implement playwright fetch
    raise NotImplementedError("Playwright fetcher not yet implemented")
