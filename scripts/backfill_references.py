"""
One-time backfill script: find and write cross-references for all existing records.

Usage: python -m scripts.backfill_references
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from notion_client import AsyncClient

load_dotenv()

# Rate-limit: max ~3 req/sec for Notion API
_NOTION_DELAY = 0.35


async def main() -> None:
    notion_key = os.environ.get("NOTION_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    rnd_page_id = os.environ.get("NOTION_RND_PAGE_ID")

    if not all([notion_key, anthropic_key, rnd_page_id]):
        logger.error("Missing required env vars: NOTION_API_KEY, ANTHROPIC_API_KEY, NOTION_RND_PAGE_ID")
        sys.exit(1)

    assert notion_key and anthropic_key and rnd_page_id  # narrow types

    client = AsyncClient(auth=notion_key)

    # Find the AI Sources database
    db_id = await _find_database(client, rnd_page_id)
    if not db_id:
        logger.error("AI Sources database not found")
        sys.exit(1)

    # Load all records
    records = await _load_all_records(client, db_id)
    logger.info(f"Loaded {len(records)} records from AI Sources")

    if len(records) < 2:
        logger.info("Not enough records to cross-reference")
        return

    # Track processed pairs to avoid duplicates
    processed_pairs: set[tuple[str, str]] = set()

    # Load existing relations to skip already-linked pairs
    existing_relations = await _load_existing_relations(client, records)
    processed_pairs.update(existing_relations)
    logger.info(f"Found {len(existing_relations)} existing relation pairs — will skip these")

    total_relations = 0

    for i, record in enumerate(records):
        logger.info(f"Processing {i + 1}/{len(records)}: {record['title']}")

        # Find candidates with overlap (excluding self and already-processed pairs)
        candidates = _find_overlap_candidates(record, records, processed_pairs)
        if not candidates:
            continue

        # Claude verification
        related_ids = await _verify_candidates(record, candidates, anthropic_key)
        if not related_ids:
            continue

        # Write relations
        relation_items = [{"id": pid} for pid in related_ids]
        await client.pages.update(
            page_id=record["page_id"],
            properties={"Related Sources": {"relation": relation_items}},
        )
        await asyncio.sleep(_NOTION_DELAY)

        # Mark pairs as processed
        for rid in related_ids:
            pair = _make_pair(record["page_id"], rid)
            processed_pairs.add(pair)

        total_relations += len(related_ids)
        logger.info(f"  → {len(related_ids)} relations written")

    logger.info(f"Backfill complete: {total_relations} total relations created")


async def _find_database(client: AsyncClient, parent_page_id: str) -> str | None:
    response = await client.search(
        query="AI Sources",
        filter={"property": "object", "value": "database"},
    )
    for result in response.get("results", []):
        parent = result.get("parent", {})
        if parent.get("page_id", "").replace("-", "") == parent_page_id.replace("-", ""):
            return str(result["id"])
    return None


async def _load_all_records(client: AsyncClient, db_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    start_cursor: str | None = None

    while True:
        query_kwargs: dict[str, Any] = {"database_id": db_id, "page_size": 100}
        if start_cursor:
            query_kwargs["start_cursor"] = start_cursor

        response = await client.databases.query(**query_kwargs)

        for page in response.get("results", []):
            props = page.get("properties", {})
            title_prop = props.get("Title", {}).get("title", [])
            title = title_prop[0]["plain_text"] if title_prop else ""
            tags = [opt["name"] for opt in props.get("Tags", {}).get("multi_select", [])]
            topics = [opt["name"] for opt in props.get("Topic", {}).get("multi_select", [])]

            records.append(
                {
                    "page_id": page["id"],
                    "title": title,
                    "tags": tags,
                    "topics": topics,
                }
            )

        if not response.get("has_more"):
            break
        start_cursor = response.get("next_cursor")
        await asyncio.sleep(_NOTION_DELAY)

    return records


async def _load_existing_relations(
    client: AsyncClient,
    records: list[dict[str, Any]],
) -> set[tuple[str, str]]:
    """Load existing 'Related Sources' relations to avoid creating duplicates."""
    pairs: set[tuple[str, str]] = set()

    for record in records:
        try:
            page = await client.pages.retrieve(page_id=record["page_id"])
            relation = page.get("properties", {}).get("Related Sources", {}).get("relation", [])
            for rel in relation:
                pairs.add(_make_pair(record["page_id"], rel["id"]))
            await asyncio.sleep(_NOTION_DELAY)
        except Exception as exc:
            logger.warning(f"Failed to load relations for {record['page_id']}: {exc}")

    return pairs


def _make_pair(id_a: str, id_b: str) -> tuple[str, str]:
    """Create a canonical pair (sorted) to avoid checking both directions."""
    return (min(id_a, id_b), max(id_a, id_b))


def _find_overlap_candidates(
    record: dict[str, Any],
    all_records: list[dict[str, Any]],
    processed_pairs: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Filter records with tag/topic overlap, excluding self and already-processed pairs."""
    record_tags = set(record["tags"])
    record_topics = set(record["topics"])
    candidates: list[dict[str, Any]] = []

    for other in all_records:
        if other["page_id"] == record["page_id"]:
            continue

        pair = _make_pair(record["page_id"], other["page_id"])
        if pair in processed_pairs:
            continue

        shared_tags = record_tags & set(other["tags"])
        shared_topics = record_topics & set(other["topics"])

        if len(shared_tags) >= 2 or len(shared_topics) >= 1:
            candidates.append(other)

    return candidates


async def _verify_candidates(
    record: dict[str, Any],
    candidates: list[dict[str, Any]],
    api_key: str,
) -> list[str]:
    """Claude Haiku verification of candidate relevance."""
    import anthropic

    from bot.analyzer.json_utils import strip_markdown_json
    from bot.analyzer.prompts import CROSS_REFERENCE_SYSTEM

    new_info = f"Title: {record['title']}\nTags: {', '.join(record['tags'])}\nTopics: {', '.join(record['topics'])}"

    candidate_lines = []
    for c in candidates:
        candidate_lines.append(f"- ID: {c['page_id']}\n  Title: {c['title']}\n  Tags: {', '.join(c['tags'])}")

    user_prompt = f"NEW RECORD:\n{new_info}\n\nCANDIDATES:\n{''.join(candidate_lines)}"

    client = anthropic.AsyncAnthropic(api_key=api_key)

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=CROSS_REFERENCE_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        block = response.content[0]
        raw_text = block.text if hasattr(block, "text") else ""  # type: ignore[union-attr]
        text = strip_markdown_json(raw_text.strip())
        parsed = json.loads(text)
        related = parsed.get("related", [])
        return [item["page_id"] for item in related if "page_id" in item]
    except Exception as exc:
        logger.warning(f"Claude verification failed for {record['title']}: {exc}")
        return []


if __name__ == "__main__":
    asyncio.run(main())
