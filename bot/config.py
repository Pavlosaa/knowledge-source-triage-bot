"""Configuration loading and validation. Fails fast at startup if required vars are missing."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


@dataclass(frozen=True)
class Config:
    # Telegram
    telegram_bot_token: str
    telegram_group_id: int

    # X.com
    twitter_username: str
    twitter_password: str
    twitter_email: str

    # Claude
    anthropic_api_key: str

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
    twitter_username = require("TWITTER_USERNAME")
    twitter_password = require("TWITTER_PASSWORD")
    twitter_email = require("TWITTER_EMAIL")
    anthropic_api_key = require("ANTHROPIC_API_KEY")
    notion_api_key = require("NOTION_API_KEY")
    notion_rnd_page_id = require("NOTION_RND_PAGE_ID")
    notion_projects_page_id = require("NOTION_PROJECTS_PAGE_ID")
    github_token = optional("GITHUB_TOKEN")

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
        twitter_username=twitter_username,
        twitter_password=twitter_password,
        twitter_email=twitter_email,
        anthropic_api_key=anthropic_api_key,
        notion_api_key=notion_api_key,
        notion_rnd_page_id=notion_rnd_page_id,
        notion_projects_page_id=notion_projects_page_id,
        github_token=github_token,
    )
