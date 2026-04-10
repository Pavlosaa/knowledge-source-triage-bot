"""Tests for /accept command handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import MessageEntity

from bot.telegram.handler import (
    _extract_url_from_entities,
    _is_fetch_failure,
    accept_command,
)


class TestExtractUrlFromEntities:
    def test_text_link_entity(self):
        entity = MagicMock(spec=MessageEntity)
        entity.type = MessageEntity.TEXT_LINK
        entity.url = "https://example.com/article"
        assert _extract_url_from_entities((entity,), "some text") == "https://example.com/article"

    def test_url_entity(self):
        entity = MagicMock(spec=MessageEntity)
        entity.type = MessageEntity.URL
        entity.url = None
        entity.offset = 5
        entity.length = 19
        text = "Link https://example.com here"
        assert _extract_url_from_entities((entity,), text) == "https://example.com"

    def test_no_url_entities(self):
        entity = MagicMock(spec=MessageEntity)
        entity.type = MessageEntity.BOLD
        entity.url = None
        assert _extract_url_from_entities((entity,), "bold text") is None

    def test_none_entities(self):
        assert _extract_url_from_entities(None, "text") is None

    def test_empty_entities(self):
        assert _extract_url_from_entities((), "text") is None


class TestIsFetchFailure:
    def test_fetch_failure_keywords(self):
        assert _is_fetch_failure("Zdroj nedostupný") is True
        assert _is_fetch_failure("Chyba při stahování") is True
        assert _is_fetch_failure("API dočasně nedostupné") is True

    def test_credibility_rejection(self):
        assert _is_fetch_failure("Nízká věrohodnost") is False
        assert _is_fetch_failure("Low credibility (1/5): spam") is False


class TestAcceptCommand:
    @pytest.mark.asyncio()
    async def test_no_reply_shows_error(self):
        update = MagicMock()
        update.message.reply_to_message = None
        update.message.reply_text = AsyncMock()

        await accept_command(update, MagicMock())

        update.message.reply_text.assert_awaited_once()
        call_args = update.message.reply_text.call_args
        assert "Odpověz na zprávu" in call_args[0][0]

    @pytest.mark.asyncio()
    async def test_reply_to_non_bot_shows_error(self):
        update = MagicMock()
        update.message.reply_to_message.from_user.is_bot = False
        update.message.reply_text = AsyncMock()

        await accept_command(update, MagicMock())

        call_args = update.message.reply_text.call_args
        assert "Odpověz na zprávu" in call_args[0][0]

    @pytest.mark.asyncio()
    async def test_no_url_in_reply_shows_error(self):
        update = MagicMock()
        update.message.reply_to_message.from_user.is_bot = True
        update.message.reply_to_message.entities = ()
        update.message.reply_to_message.text = "No URL here"
        update.message.reply_text = AsyncMock()

        await accept_command(update, MagicMock())

        call_args = update.message.reply_text.call_args
        assert "Nepodařilo se najít URL" in call_args[0][0]

    @pytest.mark.asyncio()
    async def test_credibility_override_calls_pipeline_with_skip(self):
        """Reply to credibility rejection skips Phase 1."""
        url_entity = MagicMock(spec=MessageEntity)
        url_entity.type = MessageEntity.TEXT_LINK
        url_entity.url = "https://example.com/article"

        update = MagicMock()
        update.message.reply_to_message.from_user.is_bot = True
        update.message.reply_to_message.entities = (url_entity,)
        update.message.reply_to_message.text = "❌ Nízká věrohodnost (1/5)"
        update.message.reply_text = AsyncMock()
        update.message.message_id = 123

        mock_result = MagicMock()
        mock_result.has_value = True
        mock_pipeline = AsyncMock(return_value=[mock_result])
        mock_format = MagicMock(return_value="✅ Processed")

        context = MagicMock()
        context.bot_data = {"pipeline_fn": mock_pipeline, "format_fn": mock_format}

        with patch.object(update.message, "reply_text", new=AsyncMock()) as reply_mock:
            placeholder = AsyncMock()
            reply_mock.return_value = placeholder

            await accept_command(update, context)

        mock_pipeline.assert_awaited_once_with(
            "https://example.com/article",
            skip_credibility=True,
            is_override=True,
        )

    @pytest.mark.asyncio()
    async def test_fetch_failure_override_runs_with_phase1(self):
        """Reply to fetch failure retry does not skip Phase 1."""
        url_entity = MagicMock(spec=MessageEntity)
        url_entity.type = MessageEntity.TEXT_LINK
        url_entity.url = "https://example.com/article"

        update = MagicMock()
        update.message.reply_to_message.from_user.is_bot = True
        update.message.reply_to_message.entities = (url_entity,)
        update.message.reply_to_message.text = "⚠️ Zdroj nedostupný"
        update.message.reply_text = AsyncMock()
        update.message.message_id = 456

        mock_result = MagicMock()
        mock_result.has_value = True
        mock_pipeline = AsyncMock(return_value=[mock_result])
        mock_format = MagicMock(return_value="✅ Processed")

        context = MagicMock()
        context.bot_data = {"pipeline_fn": mock_pipeline, "format_fn": mock_format}

        with patch.object(update.message, "reply_text", new=AsyncMock()):
            await accept_command(update, context)

        mock_pipeline.assert_awaited_once_with(
            "https://example.com/article",
            skip_credibility=False,
            is_override=True,
        )
