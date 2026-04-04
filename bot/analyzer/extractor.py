"""Extract GitHub repository URLs from fetched content."""

from __future__ import annotations

import re
from typing import Any

from bot.fetcher.github import RepoContent, extract_repo_coords

# Cap discovered repos to limit API costs
_MAX_DISCOVERED_REPOS = 5

# GitHub URL pattern for scanning text bodies
_GITHUB_URL_RE = re.compile(r"https?://github\.com/[^\s\"'<>\)]+")


def extract_github_urls(fetched: Any, source_url: str) -> list[str]:
    """
    Scan fetched content for GitHub repo URLs.

    Returns deduplicated, canonical GitHub repo URLs (max _MAX_DISCOVERED_REPOS).
    Excludes the source URL itself. Returns empty list for RepoContent (depth limit).
    """
    # Depth limit: never follow links from a GitHub README
    if isinstance(fetched, RepoContent):
        return []

    raw_text = _get_scannable_text(fetched)
    if not raw_text:
        return []

    # Find all GitHub URLs in the text
    urls = _GITHUB_URL_RE.findall(raw_text)

    # Also check embedded_urls on TweetContent
    embedded = getattr(fetched, "embedded_urls", None)
    if embedded:
        urls.extend(embedded)

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


def _canonicalize_github_url(url: str) -> str | None:
    """Extract and canonicalize a GitHub repo URL, or return None if not a valid repo."""
    coords = extract_repo_coords(url)
    if not coords:
        return None
    owner, repo = coords
    return f"https://github.com/{owner}/{repo}"
