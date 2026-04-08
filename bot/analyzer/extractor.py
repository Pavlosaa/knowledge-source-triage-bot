"""Extract GitHub repository URLs from fetched content."""

from __future__ import annotations

import re
from typing import Any

import httpx
from loguru import logger

from bot.fetcher.github import RepoContent, extract_repo_coords

# Cap discovered repos to limit API costs
_MAX_DISCOVERED_REPOS = 5

# GitHub URL pattern for scanning text bodies
_GITHUB_URL_RE = re.compile(r"https?://github\.com/[^\s\"'<>\)]+")


async def extract_github_urls(fetched: Any, source_url: str) -> list[str]:
    """
    Scan fetched content for GitHub repo URLs.

    Returns deduplicated, canonical GitHub repo URLs (max _MAX_DISCOVERED_REPOS).
    Excludes the source URL itself. Returns empty list for RepoContent (depth limit).
    Resolves t.co shortlinks to find hidden GitHub URLs.
    """
    # Depth limit: never follow links from a GitHub README
    if isinstance(fetched, RepoContent):
        return []

    raw_text = _get_scannable_text(fetched)

    # Find all GitHub URLs in the text
    urls: list[str] = _GITHUB_URL_RE.findall(raw_text) if raw_text else []

    # Also check embedded_urls on TweetContent (may contain t.co shortlinks)
    embedded = getattr(fetched, "embedded_urls", None)
    if embedded:
        for embedded_url in embedded:
            resolved = await _resolve_shortlink(embedded_url)
            urls.append(resolved)

    # Canonicalize and deduplicate
    source_canonical = _canonicalize_github_url(source_url)
    seen: set[str] = set()
    result: list[str] = []

    for url in urls:
        canonical = _canonicalize_github_url(url)
        if not canonical:
            continue
        if canonical == source_canonical:
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        result.append(canonical)

        if len(result) >= _MAX_DISCOVERED_REPOS:
            break

    return result


def _get_scannable_text(fetched: Any) -> str:
    """Extract scannable text from fetched content objects."""
    # TweetContent
    text = getattr(fetched, "text", None)
    if text is not None:
        return str(text)

    # ArticleContent / PageContent
    body = getattr(fetched, "body", None)
    if body is not None:
        return str(body)

    return ""


_SHORTLINK_DOMAINS = {"t.co", "bit.ly", "tinyurl.com", "ow.ly"}


async def _resolve_shortlink(url: str) -> str:
    """Follow redirects on shortlink URLs to get the final destination. Returns original URL on failure."""
    try:
        from urllib.parse import urlparse

        domain = urlparse(url).hostname or ""
        if domain not in _SHORTLINK_DOMAINS:
            return url

        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.head(url)
            resolved = str(response.url)
            if resolved != url:
                logger.debug(f"Resolved shortlink: {url} → {resolved}")
            return resolved
    except Exception as exc:
        logger.debug(f"Shortlink resolution failed for {url}: {exc}")
        return url


def _canonicalize_github_url(url: str) -> str | None:
    """Extract and canonicalize a GitHub repo URL, or return None if not a valid repo."""
    coords = extract_repo_coords(url)
    if not coords:
        return None
    owner, repo = coords
    return f"https://github.com/{owner}/{repo}"
