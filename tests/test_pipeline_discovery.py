"""Tests for run_pipeline_with_discovery orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.analyzer.pipeline import AnalysisResult, run_pipeline_with_discovery


@dataclass
class FakeArticle:
    title: str = ""
    body: str = ""


def _make_config() -> MagicMock:
    config = MagicMock()
    config.anthropic_api_key = "test-key"
    config.github_token = "test-token"
    config.scrapfly_api_key = None
    return config


def _make_writer() -> MagicMock:
    writer = MagicMock()
    writer.database_id = "db-1"
    writer.client = MagicMock()
    writer.client.pages = MagicMock()
    writer.client.pages.update = AsyncMock()
    return writer


def _make_projects() -> MagicMock:
    projects = MagicMock()
    projects.get_context = AsyncMock(return_value="User projects context")
    return projects


class TestRunPipelineWithDiscovery:
    @pytest.mark.asyncio()
    async def test_no_discovery_single_result(self) -> None:
        """Article with no GitHub URLs returns single-element list."""
        parent = AnalysisResult(
            url="https://example.com/article",
            has_value=True,
            title="Test Article",
            fetched_content=FakeArticle(body="No GitHub links here"),
        )

        with patch("bot.analyzer.pipeline.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = parent

            results = await run_pipeline_with_discovery(
                "https://example.com/article",
                _make_config(),
                _make_writer(),
                _make_projects(),
            )

        assert len(results) == 1
        assert results[0].url == "https://example.com/article"

    @pytest.mark.asyncio()
    async def test_discovery_with_two_repos(self) -> None:
        """Article with 2 GitHub URLs returns 3-element list."""
        parent = AnalysisResult(
            url="https://example.com/article",
            has_value=True,
            title="Test Article",
            core_summary="An article about repos",
            fetched_content=FakeArticle(body="Check https://github.com/owner/repo1 and https://github.com/owner/repo2"),
            notion_page_id="page-parent",
        )

        repo1_result = AnalysisResult(
            url="https://github.com/owner/repo1",
            has_value=True,
            notion_page_id="page-repo1",
        )
        repo2_result = AnalysisResult(
            url="https://github.com/owner/repo2",
            has_value=True,
            notion_page_id="page-repo2",
        )

        call_count = 0

        async def mock_pipeline_side_effect(url, config, writer, projects, source_context=None, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return parent
            if call_count == 2:
                assert source_context is not None
                return repo1_result
            return repo2_result

        writer = _make_writer()

        with patch(
            "bot.analyzer.pipeline.run_pipeline",
            new_callable=AsyncMock,
            side_effect=mock_pipeline_side_effect,
        ):
            results = await run_pipeline_with_discovery(
                "https://example.com/article",
                _make_config(),
                writer,
                _make_projects(),
            )

        assert len(results) == 3
        assert results[0].url == "https://example.com/article"
        assert results[1].url == "https://github.com/owner/repo1"
        assert results[2].url == "https://github.com/owner/repo2"

        # Verify sibling cross-referencing was called
        assert writer.client.pages.update.call_count >= 2

    @pytest.mark.asyncio()
    async def test_fetch_failure_no_discovery(self) -> None:
        """Fetch failure returns single failed result, no discovery."""
        parent = AnalysisResult(
            url="https://example.com/broken",
            has_value=False,
            fetch_failed=True,
        )

        with patch("bot.analyzer.pipeline.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = parent

            results = await run_pipeline_with_discovery(
                "https://example.com/broken",
                _make_config(),
                _make_writer(),
                _make_projects(),
            )

        assert len(results) == 1
        assert results[0].fetch_failed is True
        mock_pipeline.assert_called_once()

    @pytest.mark.asyncio()
    async def test_duplicate_no_discovery(self) -> None:
        """Duplicate URL returns single result, no discovery."""
        parent = AnalysisResult(
            url="https://example.com/dup",
            has_value=False,
            duplicate_of={"url": "https://notion.so/page", "date": "2026-01-01"},
        )

        with patch("bot.analyzer.pipeline.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = parent

            results = await run_pipeline_with_discovery(
                "https://example.com/dup",
                _make_config(),
                _make_writer(),
                _make_projects(),
            )

        assert len(results) == 1
        assert results[0].duplicate_of is not None

    @pytest.mark.asyncio()
    async def test_source_context_passed_to_discovered_repos(self) -> None:
        """Source context from parent is passed to discovered repo pipelines."""
        parent = AnalysisResult(
            url="https://example.com/article",
            has_value=True,
            title="Parent Title",
            core_summary="Parent summary",
            fetched_content=FakeArticle(body="See https://github.com/owner/repo"),
        )

        repo_result = AnalysisResult(
            url="https://github.com/owner/repo",
            has_value=True,
        )

        calls: list[dict] = []

        async def mock_pipeline(url, config, writer, projects, source_context=None, **kwargs):
            calls.append({"url": url, "source_context": source_context})
            if source_context is None:
                return parent
            return repo_result

        with patch("bot.analyzer.pipeline.run_pipeline", new_callable=AsyncMock, side_effect=mock_pipeline):
            await run_pipeline_with_discovery(
                "https://example.com/article",
                _make_config(),
                _make_writer(),
                _make_projects(),
            )

        # First call (parent) has no source_context, second (repo) has one
        assert calls[0]["source_context"] is None
        assert calls[1]["source_context"] is not None
        assert "Parent Title" in calls[1]["source_context"]
