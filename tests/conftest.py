"""Shared test fixtures for the triage bot."""

import pytest


@pytest.fixture()
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set minimal environment variables required by the bot."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_GROUP_ID", "-1001234567890")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("NOTION_API_KEY", "test-notion-key")
    monkeypatch.setenv("NOTION_RND_PAGE_ID", "test-rnd-page-id")
    monkeypatch.setenv("NOTION_PROJECTS_PAGE_ID", "test-projects-page-id")
