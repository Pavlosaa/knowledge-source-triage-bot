"""Cross-referencing logic: find related sources and write Notion relations."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import anthropic
from loguru import logger

from bot.analyzer.json_utils import strip_markdown_json
from bot.analyzer.prompts import CROSS_REFERENCE_SYSTEM

if TYPE_CHECKING:
    from notion_client import AsyncClient

    from bot.analyzer.pipeline import AnalysisResult


# Minimum overlap thresholds for candidate filtering
_MIN_SHARED_TAGS = 2
_MIN_SHARED_TOPICS = 1

# Max candidates to send to Claude for semantic verification
_MAX_CANDIDATES_FOR_CLAUDE = 15

# Overlap score weights
_TAG_WEIGHT = 1
_TOPIC_WEIGHT = 2


async def find_related_sources(
    client: AsyncClient,
    db_id: str,
    new_record: AnalysisResult,
    new_page_id: str,
    api_key: str,
) -> list[str]:
    """
    Find existing records related to the new one.

    1. Query all records from DB
    2. Filter by tag/topic overlap
    3. Claude (Haiku) semantic verification
    4. Return list of related page IDs
    """
    candidates = await _query_candidates(client, db_id, new_page_id)
    if not candidates:
        return []

    filtered = _filter_by_overlap(candidates, new_record)
    if not filtered:
        logger.debug("No candidates passed tag/topic overlap filter")
        return []

    logger.info(f"Cross-ref: {len(filtered)} candidates passed overlap filter")
    return await _verify_with_claude(new_record, filtered, api_key)


async def write_relations(
    client: AsyncClient,
    new_page_id: str,
    related_page_ids: list[str],
) -> None:
    """Update the new page's 'Related Sources' relation. Notion handles back-references."""
    relation_items = [{"id": pid} for pid in related_page_ids]
    await client.pages.update(
        page_id=new_page_id,
        properties={
            "Related Sources": {"relation": relation_items},
        },
    )
    logger.info(f"Wrote {len(related_page_ids)} relations for page {new_page_id}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _query_candidates(
    client: AsyncClient,
    db_id: str,
    exclude_page_id: str,
) -> list[dict[str, Any]]:
    """Fetch all records from the DB, paginated, extracting relevant fields."""
    candidates: list[dict[str, Any]] = []
    start_cursor: str | None = None

    while True:
        query_kwargs: dict[str, Any] = {
            "database_id": db_id,
            "page_size": 100,
        }
        if start_cursor:
            query_kwargs["start_cursor"] = start_cursor

        response = await client.databases.query(**query_kwargs)

        for page in response.get("results", []):
            page_id = page["id"]
            if page_id == exclude_page_id:
                continue

            props = page.get("properties", {})
            candidates.append(
                {
                    "page_id": page_id,
                    "title": _extract_title(props),
                    "tags": _extract_multi_select(props, "Tags"),
                    "topics": _extract_multi_select(props, "Topic"),
                    "summary": _extract_summary(page),
                }
            )

        if not response.get("has_more"):
            break
        start_cursor = response.get("next_cursor")

    logger.debug(f"Queried {len(candidates)} candidate records from Notion")
    return candidates


def _filter_by_overlap(
    candidates: list[dict[str, Any]],
    new_record: AnalysisResult,
) -> list[dict[str, Any]]:
    """Keep candidates with sufficient tag or topic overlap, ranked by overlap score."""
    new_tags = set(new_record.tags)
    new_topics = set(new_record.topics)
    scored: list[tuple[int, dict[str, Any]]] = []

    for candidate in candidates:
        shared_tags = new_tags & set(candidate["tags"])
        shared_topics = new_topics & set(candidate["topics"])

        if len(shared_tags) >= _MIN_SHARED_TAGS or len(shared_topics) >= _MIN_SHARED_TOPICS:
            score = len(shared_tags) * _TAG_WEIGHT + len(shared_topics) * _TOPIC_WEIGHT
            scored.append((score, candidate))

    # Sort by overlap score descending, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    return [candidate for _, candidate in scored[:_MAX_CANDIDATES_FOR_CLAUDE]]


async def _verify_with_claude(
    new_record: AnalysisResult,
    candidates: list[dict[str, Any]],
    api_key: str,
) -> list[str]:
    """Ask Claude to verify which candidates are genuinely related."""
    new_info = (
        f"Title: {new_record.title}\n"
        f"Summary: {new_record.core_summary}\n"
        f"Tags: {', '.join(new_record.tags)}\n"
        f"Topics: {', '.join(new_record.topics)}"
    )

    candidate_lines = []
    for c in candidates:
        candidate_lines.append(
            f"- ID: {c['page_id']}\n  Title: {c['title']}\n  Summary: {c['summary']}\n  Tags: {', '.join(c['tags'])}"
        )

    user_prompt = f"NEW RECORD:\n{new_info}\n\nCANDIDATES:\n{''.join(candidate_lines)}"

    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=CROSS_REFERENCE_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    block = response.content[0]
    raw_text = block.text if hasattr(block, "text") else ""  # type: ignore[union-attr]
    text = strip_markdown_json(raw_text.strip())

    try:
        parsed = json.loads(text)
        related = parsed.get("related", [])
        return [item["page_id"] for item in related if "page_id" in item]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning(f"Cross-reference Claude response parse failed: {exc}")
        return []


# ---------------------------------------------------------------------------
# Property extraction helpers
# ---------------------------------------------------------------------------


def _extract_title(props: dict[str, Any]) -> str:
    title_prop = props.get("Title", {}).get("title", [])
    return str(title_prop[0]["plain_text"]) if title_prop else ""


def _extract_multi_select(props: dict[str, Any], key: str) -> list[str]:
    return [opt["name"] for opt in props.get(key, {}).get("multi_select", [])]


def _extract_summary(page: dict[str, Any]) -> str:
    """Extract a short summary from page properties (title + first text block)."""
    props = page.get("properties", {})
    title = _extract_title(props)
    # We only have properties here (no page body), so title + tags is our best proxy
    tags = _extract_multi_select(props, "Tags")
    return f"{title} [{', '.join(tags)}]" if tags else title
