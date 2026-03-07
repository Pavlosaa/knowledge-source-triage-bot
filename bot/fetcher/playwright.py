"""Playwright headless browser fetcher. Fallback for JS-rendered pages."""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from playwright.async_api import async_playwright

# Tags whose text content we strip (navigation, boilerplate)
_STRIP_SELECTORS = ["nav", "header", "footer", "aside", "[role=banner]", "[role=navigation]"]


@dataclass
class PageContent:
    url: str
    title: str | None
    body: str


async def fetch_with_playwright(url: str, timeout_ms: int = 30_000) -> PageContent:
    """
    Fetch a JS-rendered page using Playwright headless Chromium.
    Extracts title and visible body text, stripping nav/footer boilerplate.
    """
    logger.info(f"Playwright fetching: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_load_state("networkidle", timeout=timeout_ms)

            title = await page.title() or None

            # Remove boilerplate elements before extracting text
            for selector in _STRIP_SELECTORS:
                for element in await page.query_selector_all(selector):
                    await element.evaluate("el => el.remove()")

            body = await page.evaluate("document.body?.innerText || ''")
            body = _clean_text(body)

            logger.info(f"Playwright fetched {len(body)} chars from {url}")
            return PageContent(url=url, title=title, body=body)
        finally:
            await browser.close()


def _clean_text(text: str) -> str:
    """Collapse excessive whitespace."""
    lines = (line.strip() for line in text.splitlines())
    non_empty = (line for line in lines if line)
    return "\n".join(non_empty)
