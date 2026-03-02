"""Load and cache user's project descriptions from Notion for Claude context."""

from __future__ import annotations

import asyncio
import time

from loguru import logger
from notion_client import AsyncClient


class ProjectsCache:
    """In-memory cache of project descriptions. Refreshes every 24 hours."""

    TTL_SECONDS = 86_400  # 24 hours

    def __init__(self, notion_api_key: str, projects_page_id: str) -> None:
        self._client = AsyncClient(auth=notion_api_key)
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
        """Fetch project pages from Notion and build context string for Claude."""
        logger.info(f"Refreshing project context from Notion page {self._page_id}")
        try:
            response = await self._client.blocks.children.list(block_id=self._page_id)
            projects = await self._extract_projects(response["results"])
            self._context = self._build_context_string(projects)
            self._last_loaded = time.time()
            logger.info(f"Loaded {len(projects)} project(s) from Notion")
        except Exception as exc:
            logger.error(f"Failed to load projects from Notion: {exc}")
            # Keep stale context rather than returning empty
            if not self._context:
                self._context = "(No project context available)"

    async def _extract_projects(self, blocks: list[dict]) -> list[dict]:
        """Extract project name + description from child_page blocks."""
        projects = []
        for block in blocks:
            if block.get("type") != "child_page":
                continue
            title = block["child_page"].get("title", "").strip()
            if not title:
                continue

            description = await self._fetch_page_description(block["id"])
            projects.append({"name": title, "description": description})

        return projects

    async def _fetch_page_description(self, page_id: str) -> str:
        """Fetch the first meaningful text block from a project page as its description."""
        try:
            response = await self._client.blocks.children.list(block_id=page_id)
            for block in response["results"]:
                text = self._extract_text_from_block(block)
                if text:
                    return text[:300]  # cap at 300 chars
        except Exception as exc:
            logger.warning(f"Could not fetch description for page {page_id}: {exc}")
        return ""

    def _extract_text_from_block(self, block: dict) -> str:
        """Pull plain text from a paragraph, heading, or callout block."""
        block_type = block.get("type", "")
        if block_type not in ("paragraph", "heading_1", "heading_2", "heading_3", "callout"):
            return ""
        rich_text = block.get(block_type, {}).get("rich_text", [])
        return "".join(part.get("plain_text", "") for part in rich_text).strip()

    def _build_context_string(self, projects: list[dict]) -> str:
        if not projects:
            return "(No projects found)"
        lines = ["User's existing projects:"]
        for p in projects:
            lines.append(f"- {p['name']}: {p['description']}" if p["description"] else f"- {p['name']}")
        return "\n".join(lines)
