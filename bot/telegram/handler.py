"""Telegram message handler. Receives messages, extracts URLs, enqueues for processing."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from loguru import logger
from telegram import Message, MessageEntity, Update
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    from bot.analyzer.pipeline import AnalysisResult

# Matches http/https URLs
_URL_RE = re.compile(r"https?://[^\s]+")


def extract_urls(text: str) -> list[str]:
    """Extract all URLs from a text string."""
    return _URL_RE.findall(text)


class MessageHandler:
    """Handles incoming Telegram messages and orchestrates the analysis pipeline."""

    def __init__(self, queue: asyncio.Queue) -> None:
        self._queue = queue

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Entry point called by python-telegram-bot for each incoming message."""
        message = update.message or update.channel_post
        if not message or not message.text:
            return

        urls = extract_urls(message.text)
        if not urls:
            return

        logger.info(f"Received message with {len(urls)} URL(s): {urls}")

        # Acknowledge immediately so user knows the bot is alive
        placeholder = await message.reply_text(
            "⏳ Analyzuji...",
            reply_to_message_id=message.message_id,
        )

        # Enqueue all URLs from this message for sequential processing
        await self._queue.put((message, placeholder, urls))


def _extract_url_from_entities(entities: tuple[MessageEntity, ...] | None, text: str | None) -> str | None:
    """Extract the first URL from message entities (text_link or url type)."""
    if not entities:
        return None
    for entity in entities:
        if entity.type == MessageEntity.TEXT_LINK and entity.url:
            return str(entity.url)
        if entity.type == MessageEntity.URL and text:
            return text[entity.offset : entity.offset + entity.length]
    return None


def _is_fetch_failure(text: str) -> bool:
    """Determine if a rejection message indicates fetch failure vs credibility rejection."""
    return "nedostupný" in text.lower() or "chyba" in text.lower() or "dočasně" in text.lower()


async def accept_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /accept reply to override a rejected link."""
    message = update.message
    if not message:
        return

    # Must be a reply to a bot message
    original = message.reply_to_message
    if not original or not original.from_user or not original.from_user.is_bot:
        await message.reply_text(
            "Odpověz na zprávu s odmítnutým zdrojem.",
            reply_to_message_id=message.message_id,
        )
        return

    # Extract URL from the original rejection message
    url = _extract_url_from_entities(original.entities, original.text)
    if not url:
        await message.reply_text(
            "Nepodařilo se najít URL v původní zprávě.",
            reply_to_message_id=message.message_id,
        )
        return

    # Determine override type: fetch failure retries with Phase 1, credibility skips it
    skip_credibility = not _is_fetch_failure(original.text or "")

    logger.info(f"/accept override for {url} (skip_credibility={skip_credibility})")

    # Send placeholder
    placeholder = await message.reply_text(
        "⏳ Přehodnocuji...",
        reply_to_message_id=message.message_id,
    )

    # Run pipeline with override flags — injected via context.bot_data
    pipeline_fn: Callable[..., Awaitable[list[AnalysisResult]]] = context.bot_data["pipeline_fn"]
    format_fn: Callable[..., str] = context.bot_data["format_fn"]

    try:
        results = await pipeline_fn(url, skip_credibility=skip_credibility, is_override=True)
        reply_text = format_fn(results, original_url=url)
    except Exception as exc:
        logger.exception(f"/accept pipeline failed for {url}: {exc}")
        reply_text = f"⚠️ Přehodnocení selhalo: {type(exc).__name__}. Zkus znovu později."

    try:
        await placeholder.delete()
        await message.reply_text(
            reply_text,
            reply_to_message_id=message.message_id,
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.error(f"Failed to send /accept reply: {exc}")


async def process_queue(
    queue: asyncio.Queue[Any],
    pipeline_fn: Callable[..., Awaitable[Any]],
    format_fn: Callable[..., str],
) -> None:
    """
    Consume the message queue sequentially.
    Runs forever as a background task.

    Args:
        queue: asyncio.Queue of (original_message, placeholder_message, urls)
        pipeline_fn: async callable(url) -> list[AnalysisResult]
        format_fn: callable(list[AnalysisResult], original_url) -> str
    """
    while True:
        message: Message
        placeholder: Message
        urls: list[str]

        message, placeholder, urls = await queue.get()

        try:
            # Process first URL only for now (multi-URL support is a future extension)
            url = urls[0]
            if len(urls) > 1:
                logger.info(f"Message contains {len(urls)} URLs, processing first: {url}")

            results = await pipeline_fn(url)
            reply_text = format_fn(results, original_url=url)

        except Exception as exc:
            logger.exception(f"Pipeline failed for message {message.message_id}: {exc}")
            reply_text = f"⚠️ Analýza selhala: {type(exc).__name__}. Zkus znovu nebo kontaktuj správce."

        finally:
            queue.task_done()

        try:
            # Replace the placeholder with the real result
            await placeholder.delete()
            await message.reply_text(
                reply_text,
                reply_to_message_id=message.message_id,
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.error(f"Failed to send reply for message {message.message_id}: {exc}")
