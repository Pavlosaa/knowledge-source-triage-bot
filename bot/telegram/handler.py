"""Telegram message handler. Receives messages, extracts URLs, enqueues for processing."""

import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from loguru import logger
from telegram import Message, Update
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    pass

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
