"""GitHub REST API fetcher. Extracts repo metadata and README."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

_GITHUB_API = "https://api.github.com"
_GITHUB_URL_RE = re.compile(r"github\.com/([^/]+)/([^/?#\s]+)")

# README truncated to this many chars to keep prompt sizes reasonable
_README_MAX_CHARS = 4_000


@dataclass
class RepoContent:
    owner: str
    repo: str
    description: str | None
    stars: int
    language: str | None
    readme: str | None


def extract_repo_coords(url: str) -> tuple[str, str] | None:
    """Return (owner, repo) from a GitHub URL, or None."""
    match = _GITHUB_URL_RE.search(url)
    if not match:
        return None
    repo = match.group(2).rstrip("/")
    return match.group(1), repo


async def fetch_repo(owner: str, repo: str, token: str | None = None) -> RepoContent:
    """Fetch repo metadata and README via GitHub REST API."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
        meta = await _fetch_json(client, f"{_GITHUB_API}/repos/{owner}/{repo}")
        readme = await _fetch_readme(client, owner, repo)

    return RepoContent(
        owner=owner,
        repo=repo,
        description=meta.get("description"),
        stars=meta.get("stargazers_count", 0),
        language=meta.get("language"),
        readme=readme,
    )


async def _fetch_json(client: httpx.AsyncClient, url: str) -> dict[Any, Any]:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()  # type: ignore[no-any-return]


async def _fetch_readme(client: httpx.AsyncClient, owner: str, repo: str) -> str | None:
    try:
        data = await _fetch_json(client, f"{_GITHUB_API}/repos/{owner}/{repo}/readme")
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        truncated = content[:_README_MAX_CHARS]
        if len(content) > _README_MAX_CHARS:
            truncated += "\n... [truncated]"
        return truncated
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            logger.info(f"No README found for {owner}/{repo}")
            return None
        raise
