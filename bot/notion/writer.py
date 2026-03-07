"""
Notion writer: finds or creates the "AI Sources" database,
then creates a record for each analyzed source.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from loguru import logger
from notion_client import AsyncClient

if TYPE_CHECKING:
    from bot.analyzer.pipeline import AnalysisResult

DB_NAME = "AI Sources"

_TOPIC_COLORS: dict[str, str] = {
    "AI Tools & Libraries": "blue",
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


class NotionWriter:
    def __init__(self, notion_api_key: str, rnd_page_id: str) -> None:
        self._client = AsyncClient(auth=notion_api_key)
        self._parent_page_id = rnd_page_id
        self._database_id: str | None = None

    async def create_source_page(self, result: "AnalysisResult", source_url: str) -> str:
        """
        Create a Notion database record for the analyzed source.
        Returns the URL of the newly created page.
        """
        db_id = await self._get_or_create_database()
        page = await self._create_record(db_id, result, source_url)
        url = page["url"]
        logger.info(f"Created Notion record: {url}")
        return url

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
                    return result["id"]
        except Exception as exc:
            logger.warning(f"Database search failed: {exc}")
        return None

    async def _create_database(self) -> str:
        """Create the AI Sources database with all required properties."""
        topic_options = [
            {"name": name, "color": color}
            for name, color in _TOPIC_COLORS.items()
        ]
        content_type_options = [
            {"name": name, "color": color}
            for name, color in _CONTENT_TYPE_COLORS.items()
        ]

        db = await self._client.databases.create(
            parent={"type": "page_id", "page_id": self._parent_page_id},
            title=[{"type": "text", "text": {"content": DB_NAME}}],
            properties={
                "Title": {"title": {}},
                "Topic": {"select": {"options": topic_options}},
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
        return db["id"]

    # ------------------------------------------------------------------
    # Record creation
    # ------------------------------------------------------------------

    async def _create_record(
        self,
        db_id: str,
        result: "AnalysisResult",
        source_url: str,
    ) -> dict:
        relevant_projects = [
            r["project_name"]
            for r in (result.project_recommendations or [])
            if r.get("relevance") in ("high", "medium")
        ]

        properties = {
            "Title": {
                "title": [{"text": {"content": result.title or source_url[:80]}}]
            },
            "Discovery Score": {"number": result.discovery_score},
            "Source URL": {"url": source_url},
            "Author": {
                "rich_text": [{"text": {"content": result.author or ""}}]
            },
            "Date Added": {
                "date": {"start": datetime.now(timezone.utc).date().isoformat()}
            },
        }

        if result.content_type and result.content_type in _CONTENT_TYPE_COLORS:
            properties["Content Type"] = {"select": {"name": result.content_type}}

        if result.topic:
            properties["Topic"] = {"select": {"name": result.topic}}

        if result.tags:
            properties["Tags"] = {
                "multi_select": [{"name": tag} for tag in result.tags[:10]]
            }

        if relevant_projects:
            properties["Relevant Projects"] = {
                "multi_select": [{"name": p} for p in relevant_projects[:10]]
            }

        return await self._client.pages.create(
            parent={"database_id": db_id},
            properties=properties,
            children=self._build_body(result, source_url),
        )

    # ------------------------------------------------------------------
    # Page body blocks
    # ------------------------------------------------------------------

    def _build_body(self, result: "AnalysisResult", source_url: str) -> list[dict]:
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

        if result.project_recommendations:
            blocks.append(self._heading2("🎯 Relevance pro projekty"))
            for rec in result.project_recommendations:
                toggle_text = f"{rec['project_name']} — {rec['relevance'].upper()}"
                blocks.append(
                    self._toggle(toggle_text, children=[self._paragraph(rec["how_to_apply"])])
                )

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
        return {"object": "block", "type": "heading_2",
                "heading_2": {"rich_text": self._rich_text(text)}}

    def _paragraph(self, text: str) -> dict:
        return {"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": self._rich_text(text)}}

    def _bullet(self, text: str) -> dict:
        return {"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": self._rich_text(text)}}

    def _toggle(self, text: str, children: list[dict]) -> dict:
        return {"object": "block", "type": "toggle",
                "toggle": {"rich_text": self._rich_text(text), "children": children}}

    def _bookmark(self, url: str) -> dict:
        return {"object": "block", "type": "bookmark", "bookmark": {"url": url}}
