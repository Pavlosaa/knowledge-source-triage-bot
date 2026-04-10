"""Tests for the core analysis pipeline (Phase 2 removed, override support)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.analyzer.pipeline import run_pipeline


@pytest.fixture()
def mock_deps():
    """Create mock pipeline dependencies."""
    config = MagicMock()
    config.anthropic_api_key = "test-key"
    config.scrapfly_api_key = None
    config.github_token = None

    writer = AsyncMock()
    writer.find_existing = AsyncMock(return_value=None)
    writer.create_source_page = AsyncMock(return_value=("https://notion.so/page", "page-id-123"))
    writer.database_id = "db-123"
    writer.client = MagicMock()

    projects = AsyncMock()
    projects.get_context = AsyncMock(return_value="Projects: TestProject")

    return config, writer, projects


def _make_credibility_response(score: int = 4, reason: str = "Credible source") -> dict:
    return {"credibility_score": score, "credibility_reason": reason}


def _make_analysis_response() -> dict:
    return {
        "title": "Test Title",
        "topics": ["AI Tools & Libraries"],
        "core_summary": "A useful tool.",
        "key_principles": ["Principle 1"],
        "use_cases": ["Use case 1"],
        "real_world_example": "Example usage.",
        "discovery_score": 4,
        "tags": ["ai", "tools"],
        "project_recommendations": [],
    }


def _make_rejection_summary() -> dict:
    return {
        "brief_summary": "Content from unknown source.",
        "rejection_reason": "Zdroj nemá ověřitelnou historii.",
    }


class TestPipelineHappyPath:
    """Phase 1 passes -> Phase 3A runs -> Notion record created."""

    @pytest.mark.asyncio()
    async def test_credible_link_produces_notion_record(self, mock_deps):
        config, writer, projects = mock_deps

        with (
            patch("bot.analyzer.pipeline._fetch") as mock_fetch,
            patch("bot.analyzer.pipeline._call_claude") as mock_claude,
            patch("bot.analyzer.pipeline.find_related_sources", new_callable=AsyncMock, return_value=[]),
        ):
            mock_fetch.return_value = (MagicMock(), "Article", None)
            mock_claude.side_effect = [
                _make_credibility_response(score=4),
                _make_analysis_response(),
            ]

            result = await run_pipeline("https://example.com", config, writer, projects)

        assert result.has_value is True
        assert result.title == "Test Title"
        assert result.discovery_score == 4
        assert result.topics == ["AI Tools & Libraries"]
        writer.create_source_page.assert_awaited_once()


class TestPhase1Rejection:
    """Phase 1 credibility < 2 -> Phase 3B runs -> rejection with summary."""

    @pytest.mark.asyncio()
    async def test_low_credibility_rejects_with_summary(self, mock_deps):
        config, writer, projects = mock_deps

        with (
            patch("bot.analyzer.pipeline._fetch") as mock_fetch,
            patch("bot.analyzer.pipeline._call_claude") as mock_claude,
        ):
            mock_fetch.return_value = (MagicMock(), "Article", None)
            mock_claude.side_effect = [
                _make_credibility_response(score=1, reason="Suspicious source"),
                _make_rejection_summary(),
            ]

            result = await run_pipeline("https://spam.example.com", config, writer, projects)

        assert result.has_value is False
        assert result.brief_summary == "Content from unknown source."
        assert result.rejection_reason is not None
        writer.create_source_page.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_phase3b_failure_falls_back_to_credibility_reason(self, mock_deps):
        config, writer, projects = mock_deps

        with (
            patch("bot.analyzer.pipeline._fetch") as mock_fetch,
            patch("bot.analyzer.pipeline._call_claude") as mock_claude,
        ):
            mock_fetch.return_value = (MagicMock(), "Article", None)
            mock_claude.side_effect = [
                _make_credibility_response(score=1, reason="Spam"),
                RuntimeError("Phase 3B API error"),
            ]

            result = await run_pipeline("https://spam.example.com", config, writer, projects)

        assert result.has_value is False
        assert "Low credibility (1/5)" in (result.rejection_reason or "")


class TestPhase1GracefulDegradation:
    """Phase 1 error -> default score 3 -> Phase 3A runs."""

    @pytest.mark.asyncio()
    async def test_phase1_error_defaults_to_neutral_and_continues(self, mock_deps):
        config, writer, projects = mock_deps

        with (
            patch("bot.analyzer.pipeline._fetch") as mock_fetch,
            patch("bot.analyzer.pipeline._call_claude") as mock_claude,
            patch("bot.analyzer.pipeline.find_related_sources", new_callable=AsyncMock, return_value=[]),
        ):
            mock_fetch.return_value = (MagicMock(), "Article", None)
            mock_claude.side_effect = [
                RuntimeError("Phase 1 API error"),
                _make_analysis_response(),
            ]

            result = await run_pipeline("https://example.com", config, writer, projects)

        assert result.has_value is True
        assert result.credibility_score == 3


class TestPhase3AError:
    """Phase 3A error -> fetch_failed=True, not a rejection."""

    @pytest.mark.asyncio()
    async def test_phase3a_error_sets_fetch_failed(self, mock_deps):
        config, writer, projects = mock_deps

        with (
            patch("bot.analyzer.pipeline._fetch") as mock_fetch,
            patch("bot.analyzer.pipeline._call_claude") as mock_claude,
        ):
            mock_fetch.return_value = (MagicMock(), "Article", None)
            mock_claude.side_effect = [
                _make_credibility_response(score=4),
                RuntimeError("Claude API overloaded"),
            ]

            result = await run_pipeline("https://example.com", config, writer, projects)

        assert result.fetch_failed is True
        assert "dočasně" in (result.rejection_reason or "").lower()


class TestOverrideParams:
    """Override params: skip_credibility and is_override."""

    @pytest.mark.asyncio()
    async def test_skip_credibility_bypasses_phase1(self, mock_deps):
        config, writer, projects = mock_deps

        with (
            patch("bot.analyzer.pipeline._fetch") as mock_fetch,
            patch("bot.analyzer.pipeline._call_claude") as mock_claude,
            patch("bot.analyzer.pipeline.find_related_sources", new_callable=AsyncMock, return_value=[]),
        ):
            mock_fetch.return_value = (MagicMock(), "Article", None)
            # Only Phase 3A should be called — Phase 1 is skipped
            mock_claude.side_effect = [_make_analysis_response()]

            result = await run_pipeline(
                "https://example.com",
                config,
                writer,
                projects,
                skip_credibility=True,
                is_override=True,
            )

        assert result.has_value is True
        assert result.is_override is True
        assert result.credibility_score is None  # Phase 1 never ran

    @pytest.mark.asyncio()
    async def test_is_override_without_skip_credibility(self, mock_deps):
        """Fetch failure retry: Phase 1 runs, but result is marked as override."""
        config, writer, projects = mock_deps

        with (
            patch("bot.analyzer.pipeline._fetch") as mock_fetch,
            patch("bot.analyzer.pipeline._call_claude") as mock_claude,
            patch("bot.analyzer.pipeline.find_related_sources", new_callable=AsyncMock, return_value=[]),
        ):
            mock_fetch.return_value = (MagicMock(), "Article", None)
            mock_claude.side_effect = [
                _make_credibility_response(score=4),
                _make_analysis_response(),
            ]

            result = await run_pipeline(
                "https://example.com",
                config,
                writer,
                projects,
                is_override=True,
            )

        assert result.has_value is True
        assert result.is_override is True
        assert result.credibility_score == 4  # Phase 1 ran normally


class TestDedupCheck:
    @pytest.mark.asyncio()
    async def test_duplicate_url_returns_early(self, mock_deps):
        config, writer, projects = mock_deps
        writer.find_existing.return_value = {"url": "https://notion.so/existing"}

        result = await run_pipeline("https://example.com", config, writer, projects)

        assert result.duplicate_of is not None
        assert result.has_value is False


class TestFetchFailure:
    @pytest.mark.asyncio()
    async def test_fetch_error_returns_fetch_failed(self, mock_deps):
        config, writer, projects = mock_deps

        with patch("bot.analyzer.pipeline._fetch", side_effect=RuntimeError("Connection timeout")):
            result = await run_pipeline("https://example.com", config, writer, projects)

        assert result.fetch_failed is True
        assert "Nepodařilo se" in (result.rejection_reason or "")
