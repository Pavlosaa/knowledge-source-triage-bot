"""Configuration loading and validation. Fails fast at startup if required vars are missing."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from loguru import logger

from bot.analyzer.claude import DEFAULT_ANALYSIS_MODEL, DEFAULT_FAST_MODEL

load_dotenv()


@dataclass(frozen=True)
class Config:
    # Telegram
    telegram_bot_token: str
    telegram_group_id: int

    # X.com (ScrapFly — optional, enables tweet fetching)
    scrapfly_api_key: str | None

    # Claude
    anthropic_api_key: str
    claude_fast_model: str  # phase 1, phase 3B, cross-referencing
    claude_analysis_model: str  # phase 3A full analysis

    # Notion
    notion_api_key: str
    notion_rnd_page_id: str
    notion_projects_page_id: str

    # Optional
    github_token: str | None


def load_config() -> Config:
    """Load and validate all required environment variables. Exits if any are missing."""
    errors: list[str] = []

    def require(key: str) -> str:
        value = os.getenv(key, "").strip()
        if not value:
            errors.append(f"Missing required env var: {key}")
        return value

    def optional(key: str) -> str | None:
        value = os.getenv(key, "").strip()
        return value if value else None

    telegram_bot_token = require("TELEGRAM_BOT_TOKEN")
    telegram_group_id_raw = require("TELEGRAM_GROUP_ID")
    anthropic_api_key = require("ANTHROPIC_API_KEY")
    claude_fast_model = optional("CLAUDE_FAST_MODEL") or DEFAULT_FAST_MODEL
    claude_analysis_model = optional("CLAUDE_ANALYSIS_MODEL") or DEFAULT_ANALYSIS_MODEL
    notion_api_key = require("NOTION_API_KEY")
    notion_rnd_page_id = require("NOTION_RND_PAGE_ID")
    notion_projects_page_id = require("NOTION_PROJECTS_PAGE_ID")
    github_token = optional("GITHUB_TOKEN")
    scrapfly_api_key = optional("SCRAPFLY_API_KEY")

    if errors:
        for error in errors:
            logger.error(error)
        raise SystemExit(f"Configuration error: {len(errors)} missing env var(s). See logs above.")

    try:
        telegram_group_id = int(telegram_group_id_raw)
    except ValueError as err:
        raise SystemExit(f"TELEGRAM_GROUP_ID must be an integer, got: {telegram_group_id_raw!r}") from err

    return Config(
        telegram_bot_token=telegram_bot_token,
        telegram_group_id=telegram_group_id,
        scrapfly_api_key=scrapfly_api_key,
        anthropic_api_key=anthropic_api_key,
        claude_fast_model=claude_fast_model,
        claude_analysis_model=claude_analysis_model,
        notion_api_key=notion_api_key,
        notion_rnd_page_id=notion_rnd_page_id,
        notion_projects_page_id=notion_projects_page_id,
        github_token=github_token,
    )
