"""
Notion writer: finds or creates the "AI Sources" database,
then creates a record for each analyzed source.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

from loguru import logger
from notion_client import AsyncClient

if TYPE_CHECKING:
    from bot.analyzer.pipeline import AnalysisResult

DB_NAME = "AI Sources"

_TOPIC_COLORS: dict[str, str] = {
    "AI Tools & Libraries": "blue",
    "Tutorials": "pink",
    "Educational Content": "green",
    "Tips & Tricks": "yellow",
    "Best Practices": "purple",
    "News & Updates": "red",
    "Interesting Findings": "orange",
}

_CONTENT_TYPE_COLORS: dict[str, str] = {
    "Tweet": "blue",
    "X Article": "green",
    "GitHub": "gray",
    "Article": "orange",
}


def _canonicalize_url(url: str) -> str:
    """Normalize URL for dedup comparison: strip trailing slash, query params, fragments, www."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    host = re.sub(r"^www\.", "", host)
    path = parsed.path.rstrip("/")
    return urlunparse(("https", host, path, "", "", ""))


class NotionWriter:
    def __init__(self, notion_api_key: str, rnd_page_id: str) -> None:
        self._client = AsyncClient(auth=notion_api_key)
        self._parent_page_id = rnd_page_id
        self._database_id: str | None = None

    @property
    def client(self) -> AsyncClient:
        """Expose the Notion client for cross-referencing."""
        return self._client

    @property
    def database_id(self) -> str | None:
        """Expose the database ID for cross-referencing."""
        return self._database_id

    async def find_existing(self, source_url: str) -> dict | None:
        """
        Check if a record with this Source URL already exists in the database.
        Returns {"url": notion_page_url, "date": date_added} or None.
        """
        db_id = await self._get_or_create_database()
        canonical = _canonicalize_url(source_url)

        try:
            response = await self._client.databases.query(
                database_id=db_id,
                filter={"property": "Source URL", "url": {"equals": canonical}},
                page_size=1,
            )
            results = response.get("results", [])
            if not results:
                return None

            page = results[0]
            page_url = page["url"]
            date_prop = page.get("properties", {}).get("Date Added", {}).get("date") or {}
            date_added = date_prop.get("start")
            return {"url": page_url, "date": date_added}
        except Exception as exc:
            logger.warning(f"Dedup query failed: {exc}")
            return None

    async def create_source_page(self, result: AnalysisResult, source_url: str) -> tuple[str, str]:
        """
        Create a Notion database record for the analyzed source.
        Returns (page_url, page_id) of the newly created page.
        """
        db_id = await self._get_or_create_database()
        page = await self._create_record(db_id, result, source_url)
        url = str(page["url"])
        page_id = str(page["id"])
        logger.info(f"Created Notion record: {url}")
        return url, page_id

    # ------------------------------------------------------------------
    # Database management
    # ------------------------------------------------------------------

    async def _get_or_create_database(self) -> str:
        if self._database_id:
            return self._database_id

        db_id = await self._find_database()
        if not db_id:
            logger.info(f'Database "{DB_NAME}" not found — creating it')
            db_id = await self._create_database()

        await self._ensure_relation_property(db_id)
        self._database_id = db_id
        return db_id

    async def _find_database(self) -> str | None:
        """Search for existing AI Sources database under the parent page."""
        try:
            response = await self._client.search(
                query=DB_NAME,
                filter={"property": "object", "value": "database"},
            )
            for result in response.get("results", []):
                parent = result.get("parent", {})
                if parent.get("page_id", "").replace("-", "") == self._parent_page_id.replace("-", ""):
                    logger.info(f'Found existing database "{DB_NAME}": {result["id"]}')
                    return str(result["id"])
        except Exception as exc:
            logger.warning(f"Database search failed: {exc}")
        return None

    async def _create_database(self) -> str:
        """Create the AI Sources database with all required properties."""
        topic_options = [{"name": name, "color": color} for name, color in _TOPIC_COLORS.items()]
        content_type_options = [{"name": name, "color": color} for name, color in _CONTENT_TYPE_COLORS.items()]

        db = await self._client.databases.create(
            parent={"type": "page_id", "page_id": self._parent_page_id},
            title=[{"type": "text", "text": {"content": DB_NAME}}],
            properties={
                "Title": {"title": {}},
                "Topic": {"multi_select": {"options": topic_options}},
                "Discovery Score": {"number": {"format": "number"}},
                "Source URL": {"url": {}},
                "Content Type": {"select": {"options": content_type_options}},
                "Author": {"rich_text": {}},
                "Tags": {"multi_select": {}},
                "Date Added": {"date": {}},
                "Relevant Projects": {"multi_select": {}},
            },
        )
        logger.info(f'Created database "{DB_NAME}": {db["id"]}')
        return str(db["id"])

    async def _ensure_relation_property(self, db_id: str) -> None:
        """Add self-referencing 'Related Sources' relation property (idempotent)."""
        try:
            await self._client.databases.update(
                database_id=db_id,
                properties={
                    "Related Sources": {
                        "relation": {
                            "database_id": db_id,
                            "type": "dual_property",
                            "dual_property": {
                                "synced_property_name": "Related by",
                            },
                        },
                    },
                },
            )
            logger.debug("Ensured 'Related Sources' relation property exists")
        except Exception as exc:
            logger.warning(f"Failed to ensure relation property: {exc}")

    # ------------------------------------------------------------------
    # Record creation
    # ------------------------------------------------------------------

    async def _create_record(
        self,
        db_id: str,
        result: AnalysisResult,
        source_url: str,
    ) -> dict:
        relevant_projects = [
            r["project_name"]
            for r in (result.project_recommendations or [])
            if r.get("relevance") in ("high", "medium")
        ]

        properties = {
            "Title": {"title": [{"text": {"content": result.title or source_url[:80]}}]},
            "Discovery Score": {"number": result.discovery_score},
            "Source URL": {"url": _canonicalize_url(source_url)},
            "Author": {"rich_text": [{"text": {"content": result.author or ""}}]},
            "Date Added": {"date": {"start": datetime.now(UTC).date().isoformat()}},
        }

        if result.content_type and result.content_type in _CONTENT_TYPE_COLORS:
            properties["Content Type"] = {"select": {"name": result.content_type}}

        if result.topics:
            properties["Topic"] = {"multi_select": [{"name": t} for t in result.topics[:3]]}

        tags = list(result.tags) if result.tags else []
        if result.is_override:
            tags.append("Manual Override")
        if tags:
            properties["Tags"] = {"multi_select": [{"name": tag} for tag in tags[:10]]}

        if relevant_projects:
            properties["Relevant Projects"] = {"multi_select": [{"name": p} for p in relevant_projects[:10]]}

        return await self._client.pages.create(  # type: ignore[no-any-return]
            parent={"database_id": db_id},
            properties=properties,
            children=self._build_body(result, source_url),
        )

    # ------------------------------------------------------------------
    # Page body blocks
    # ------------------------------------------------------------------

    def _build_body(self, result: AnalysisResult, source_url: str) -> list[dict]:
        blocks: list[dict] = []

        if result.core_summary:
            blocks += [
                self._heading2("📌 Shrnutí"),
                self._paragraph(result.core_summary),
            ]

        if result.key_principles:
            blocks.append(self._heading2("🔑 Klíčové poznatky"))
            blocks += [self._bullet(p) for p in result.key_principles]

        if result.use_cases:
            blocks.append(self._heading2("💡 Využití"))
            blocks += [self._bullet(u) for u in result.use_cases]

        if result.real_world_example:
            blocks += [
                self._heading2("🌍 Příklad z praxe"),
                self._paragraph(result.real_world_example),
            ]

        if result.project_recommendations:
            blocks.append(self._heading2("🎯 Relevance pro projekty"))
            for rec in result.project_recommendations:
                toggle_text = f"{rec['project_name']} — {rec['relevance'].upper()}"
                blocks.append(self._toggle(toggle_text, children=[self._paragraph(rec["how_to_apply"])]))

        blocks += [
            self._heading2("🔗 Zdroj"),
            self._bookmark(source_url),
        ]

        return blocks

    # ------------------------------------------------------------------
    # Block helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rich_text(content: str) -> list[dict]:
        return [{"type": "text", "text": {"content": content[:2000]}}]

    def _heading2(self, text: str) -> dict:
        return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": self._rich_text(text)}}

    def _paragraph(self, text: str) -> dict:
        return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": self._rich_text(text)}}

    def _bullet(self, text: str) -> dict:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": self._rich_text(text)},
        }

    def _toggle(self, text: str, children: list[dict]) -> dict:
        return {
            "object": "block",
            "type": "toggle",
            "toggle": {"rich_text": self._rich_text(text), "children": children},
        }

    def _bookmark(self, url: str) -> dict:
        return {"object": "block", "type": "bookmark", "bookmark": {"url": url}}
