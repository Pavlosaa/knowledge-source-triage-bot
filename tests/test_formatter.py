"""Tests for Telegram message formatting."""

from __future__ import annotations

from bot.analyzer.pipeline import AnalysisResult
from bot.telegram.formatter import format_result, format_results


def _make_valuable(
    url: str = "https://example.com",
    title: str = "Test",
    score: int = 4,
    notion_url: str | None = "https://notion.so/page",
) -> AnalysisResult:
    return AnalysisResult(
        url=url,
        has_value=True,
        title=title,
        core_summary="A great resource",
        discovery_score=score,
        notion_url=notion_url,
    )


def _make_rejected(url: str = "https://example.com") -> AnalysisResult:
    return AnalysisResult(
        url=url,
        has_value=False,
        rejection_reason="Low quality content",
    )


class TestFormatResults:
    def test_single_result_delegates(self) -> None:
        """Single result produces same output as format_result."""
        result = _make_valuable()
        single = format_result(result, original_url="https://example.com")
        multi = format_results([result], original_url="https://example.com")
        assert single == multi

    def test_multiple_results_shows_repos(self) -> None:
        """Multiple results show parent + discovered repos section."""
        parent = _make_valuable(url="https://example.com/article", title="Article")
        repo1 = _make_valuable(url="https://github.com/owner/repo1", title="Repo One", score=5)
        repo2 = _make_valuable(url="https://github.com/owner/repo2", title="Repo Two", score=3)

        text = format_results([parent, repo1, repo2], original_url="https://example.com/article")

        assert "Nalezené repozitáře (2)" in text
        assert "Repo One" in text
        assert "Repo Two" in text
        assert "Notion →" in text

    def test_skipped_repos_mentioned(self) -> None:
        """Rejected repos are counted as skipped."""
        parent = _make_valuable(url="https://example.com/article")
        repo_ok = _make_valuable(url="https://github.com/owner/repo1", title="Good Repo")
        repo_bad = _make_rejected(url="https://github.com/owner/repo2")

        text = format_results([parent, repo_ok, repo_bad], original_url="https://example.com/article")

        assert "Nalezené repozitáře (2)" in text
        assert "1 repozitářů přeskočeno" in text

    def test_respects_message_limit(self) -> None:
        """Output doesn't exceed Telegram message limit."""
        parent = _make_valuable(url="https://example.com/article")
        repos = [
            _make_valuable(
                url=f"https://github.com/owner/repo-{i}",
                title=f"Repository with a very long name number {i} that takes up space",
            )
            for i in range(5)
        ]

        text = format_results([parent, *repos], original_url="https://example.com/article")
        assert len(text) <= 4096
