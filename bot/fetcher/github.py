"""GitHub REST API fetcher. Extracts repo metadata and README."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RepoContent:
    owner: str
    repo: str
    description: str | None
    stars: int
    language: str | None
    readme: str | None


_GITHUB_URL_RE = re.compile(r"github\.com/([^/]+)/([^/?#]+)")


def extract_repo_coords(url: str) -> tuple[str, str] | None:
    """Return (owner, repo) from a GitHub URL, or None."""
    match = _GITHUB_URL_RE.search(url)
    if not match:
        return None
    return match.group(1), match.group(2)


async def fetch_repo(owner: str, repo: str, token: str | None = None) -> RepoContent:
    """Fetch repo metadata and README via GitHub REST API."""
    # TODO: implement httpx calls to api.github.com
    raise NotImplementedError("GitHub fetcher not yet implemented")
