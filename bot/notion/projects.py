"""Load and cache user's project descriptions from Notion for Claude context."""

from __future__ import annotations

import asyncio
import time


class ProjectsCache:
    """In-memory cache of project descriptions. Refreshes every 24 hours."""

    TTL_SECONDS = 86_400  # 24 hours

    def __init__(self, notion_api_key: str, projects_page_id: str) -> None:
        self._api_key = notion_api_key
        self._page_id = projects_page_id
        self._context: str = ""
        self._last_loaded: float = 0.0
        self._lock = asyncio.Lock()

    async def get_context(self) -> str:
        """Return project context string, refreshing if stale."""
        async with self._lock:
            if time.time() - self._last_loaded > self.TTL_SECONDS or not self._context:
                await self._refresh()
        return self._context

    async def _refresh(self) -> None:
        # TODO: implement Notion API call to load project pages
        raise NotImplementedError("Notion projects loader not yet implemented")
