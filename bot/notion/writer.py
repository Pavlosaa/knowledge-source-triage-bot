"""Create Notion pages for analyzed knowledge sources."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.analyzer.pipeline import AnalysisResult


async def create_source_page(
    result: "AnalysisResult",
    notion_api_key: str,
    parent_page_id: str,
) -> str:
    """
    Create a Notion subpage documenting the analyzed source.
    Returns the URL of the newly created page.
    """
    # TODO: implement Notion API page creation
    raise NotImplementedError("Notion writer not yet implemented")
