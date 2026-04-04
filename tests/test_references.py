"""Tests for cross-referencing logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.analyzer.pipeline import AnalysisResult
from bot.notion.references import (
    _extract_multi_select,
    _extract_title,
    _filter_by_overlap,
    find_related_sources,
    write_relations,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_result(
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    title: str = "Test Record",
    summary: str = "Test summary",
) -> AnalysisResult:
    return AnalysisResult(
        url="https://example.com/test",
        has_value=True,
        title=title,
        core_summary=summary,
        tags=tags or [],
        topics=topics or [],
    )


def _make_candidate(
    page_id: str = "candidate-1",
    title: str = "Candidate",
    tags: list[str] | None = None,
    topics: list[str] | None = None,
) -> dict:
    return {
        "page_id": page_id,
        "title": title,
        "tags": tags or [],
        "topics": topics or [],
        "summary": f"{title} [{', '.join(tags or [])}]",
    }


# ---------------------------------------------------------------------------
# _filter_by_overlap tests
# ---------------------------------------------------------------------------


class TestFilterByOverlap:
    def test_filters_by_shared_tags(self) -> None:
        record = _make_result(tags=["LLM", "RAG", "embeddings"])
        candidates = [
            _make_candidate("c1", tags=["LLM", "RAG"]),  # 2 shared → pass
            _make_candidate("c2", tags=["LLM"]),  # 1 shared → fail
            _make_candidate("c3", tags=["React", "CSS"]),  # 0 shared → fail
        ]
        result = _filter_by_overlap(candidates, record)
        assert len(result) == 1
        assert result[0]["page_id"] == "c1"

    def test_filters_by_shared_topics(self) -> None:
        record = _make_result(topics=["AI Tools & Libraries"])
        candidates = [
            _make_candidate("c1", topics=["AI Tools & Libraries"]),  # 1 shared → pass
            _make_candidate("c2", topics=["News & Updates"]),  # 0 shared → fail
        ]
        result = _filter_by_overlap(candidates, record)
        assert len(result) == 1
        assert result[0]["page_id"] == "c1"

    def test_combined_tags_and_topics(self) -> None:
        record = _make_result(tags=["LLM", "RAG"], topics=["Best Practices"])
        candidates = [
            _make_candidate("c1", tags=["LLM"], topics=["Best Practices"]),  # topic match
            _make_candidate("c2", tags=["LLM", "RAG"]),  # tag match
            _make_candidate("c3", tags=["Vue"], topics=["News & Updates"]),  # no match
        ]
        result = _filter_by_overlap(candidates, record)
        assert len(result) == 2
        assert {r["page_id"] for r in result} == {"c1", "c2"}

    def test_empty_candidates(self) -> None:
        record = _make_result(tags=["LLM"])
        assert _filter_by_overlap([], record) == []

    def test_no_tags_or_topics(self) -> None:
        record = _make_result()
        candidates = [_make_candidate("c1", tags=["LLM"])]
        assert _filter_by_overlap(candidates, record) == []


# ---------------------------------------------------------------------------
# Property extraction tests
# ---------------------------------------------------------------------------


class TestPropertyExtraction:
    def test_extract_title(self) -> None:
        props = {"Title": {"title": [{"plain_text": "My Title"}]}}
        assert _extract_title(props) == "My Title"

    def test_extract_title_empty(self) -> None:
        assert _extract_title({}) == ""
        assert _extract_title({"Title": {"title": []}}) == ""

    def test_extract_multi_select(self) -> None:
        props = {"Tags": {"multi_select": [{"name": "LLM"}, {"name": "RAG"}]}}
        assert _extract_multi_select(props, "Tags") == ["LLM", "RAG"]

    def test_extract_multi_select_missing(self) -> None:
        assert _extract_multi_select({}, "Tags") == []


# ---------------------------------------------------------------------------
# write_relations tests
# ---------------------------------------------------------------------------


class TestWriteRelations:
    @pytest.mark.asyncio()
    async def test_writes_relation_property(self) -> None:
        mock_client = MagicMock()
        mock_client.pages.update = AsyncMock()

        await write_relations(mock_client, "page-1", ["rel-1", "rel-2"])

        mock_client.pages.update.assert_called_once_with(
            page_id="page-1",
            properties={
                "Related Sources": {
                    "relation": [{"id": "rel-1"}, {"id": "rel-2"}],
                },
            },
        )

    @pytest.mark.asyncio()
    async def test_writes_empty_list(self) -> None:
        mock_client = MagicMock()
        mock_client.pages.update = AsyncMock()

        await write_relations(mock_client, "page-1", [])

        mock_client.pages.update.assert_called_once_with(
            page_id="page-1",
            properties={"Related Sources": {"relation": []}},
        )


# ---------------------------------------------------------------------------
# find_related_sources integration (mocked)
# ---------------------------------------------------------------------------


class TestFindRelatedSources:
    @pytest.mark.asyncio()
    async def test_returns_empty_when_no_candidates(self) -> None:
        mock_client = MagicMock()
        mock_client.databases.query = AsyncMock(return_value={"results": [], "has_more": False})

        result = await find_related_sources(mock_client, "db-1", _make_result(), "page-new", "test-key")
        assert result == []

    @pytest.mark.asyncio()
    async def test_returns_empty_when_no_overlap(self) -> None:
        mock_client = MagicMock()
        mock_client.databases.query = AsyncMock(
            return_value={
                "results": [
                    {
                        "id": "page-old",
                        "properties": {
                            "Title": {"title": [{"plain_text": "Old Record"}]},
                            "Tags": {"multi_select": [{"name": "React"}]},
                            "Topic": {"multi_select": [{"name": "News & Updates"}]},
                        },
                    }
                ],
                "has_more": False,
            }
        )

        record = _make_result(tags=["LLM"], topics=["AI Tools & Libraries"])
        result = await find_related_sources(mock_client, "db-1", record, "page-new", "test-key")
        assert result == []

    @pytest.mark.asyncio()
    async def test_calls_claude_for_overlapping_candidates(self) -> None:
        mock_client = MagicMock()
        mock_client.databases.query = AsyncMock(
            return_value={
                "results": [
                    {
                        "id": "page-old",
                        "properties": {
                            "Title": {"title": [{"plain_text": "Old Record"}]},
                            "Tags": {"multi_select": [{"name": "LLM"}, {"name": "RAG"}]},
                            "Topic": {"multi_select": [{"name": "AI Tools & Libraries"}]},
                        },
                    }
                ],
                "has_more": False,
            }
        )

        record = _make_result(tags=["LLM", "RAG"], topics=["AI Tools & Libraries"])

        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = '{"related": [{"page_id": "page-old", "reason": "Oba se zabývají RAG"}]}'
        mock_response.content = [mock_block]

        mock_claude_client = AsyncMock()
        mock_claude_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("bot.notion.references.anthropic") as mock_anthropic_mod:
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_claude_client

            result = await find_related_sources(mock_client, "db-1", record, "page-new", "test-key")

        assert result == ["page-old"]


# ---------------------------------------------------------------------------
# Backfill dedup tests
# ---------------------------------------------------------------------------


_has_notion_client = False
try:
    import notion_client  # noqa: F401

    _has_notion_client = True
except ImportError:
    pass


@pytest.mark.skipif(not _has_notion_client, reason="notion_client not installed")
class TestBackfillDedup:
    def test_make_pair_canonical(self) -> None:
        from scripts.backfill_references import _make_pair

        assert _make_pair("a", "b") == ("a", "b")
        assert _make_pair("b", "a") == ("a", "b")

    def test_find_overlap_candidates_excludes_self(self) -> None:
        from scripts.backfill_references import _find_overlap_candidates

        record = {"page_id": "p1", "tags": ["LLM", "RAG"], "topics": []}
        all_records = [
            record,
            {"page_id": "p2", "tags": ["LLM", "RAG"], "topics": []},
        ]
        candidates = _find_overlap_candidates(record, all_records, set())
        assert len(candidates) == 1
        assert candidates[0]["page_id"] == "p2"

    def test_find_overlap_candidates_excludes_processed(self) -> None:
        from scripts.backfill_references import _find_overlap_candidates, _make_pair

        record = {"page_id": "p1", "tags": ["LLM", "RAG"], "topics": []}
        all_records = [
            record,
            {"page_id": "p2", "tags": ["LLM", "RAG"], "topics": []},
        ]
        processed = {_make_pair("p1", "p2")}
        candidates = _find_overlap_candidates(record, all_records, processed)
        assert candidates == []
