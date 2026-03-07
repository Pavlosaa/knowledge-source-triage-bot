"""Entry point. Wires config, queue, handlers, and starts the Telegram bot."""

import asyncio
import functools
import sys

from loguru import logger
from telegram.ext import ApplicationBuilder, MessageHandler as TGMessageHandler, filters

from bot.config import load_config
from bot.telegram.handler import MessageHandler, process_queue
from bot.telegram.formatter import format_result
from bot.analyzer.pipeline import run_pipeline
from bot.notion.writer import NotionWriter
from bot.notion.projects import ProjectsCache

# --- Logging setup ---
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
logger.add("logs/bot.log", rotation="10 MB", retention="7 days", level="DEBUG")
logger.add("logs/errors.log", rotation="10 MB", retention="7 days", level="ERROR")


async def main() -> None:
    config = load_config()
    logger.info("Configuration loaded.")

    writer = NotionWriter(
        notion_api_key=config.notion_api_key,
        rnd_page_id=config.notion_rnd_page_id,
    )
    projects = ProjectsCache(
        notion_api_key=config.notion_api_key,
        projects_page_id=config.notion_projects_page_id,
    )

    pipeline_fn = functools.partial(run_pipeline, config=config, writer=writer, projects=projects)

    queue: asyncio.Queue = asyncio.Queue()
    handler = MessageHandler(queue)

    app = (
        ApplicationBuilder()
        .token(config.telegram_bot_token)
        .build()
    )

    # Listen to messages in the configured group only
    app.add_handler(
        TGMessageHandler(
            filters.Chat(config.telegram_group_id) & filters.TEXT,
            handler.handle,
        )
    )

    # Start the queue processor as a background task
    async with app:
        await app.start()
        logger.info("Bot started. Listening for messages...")

        queue_task = asyncio.create_task(
            process_queue(
                queue=queue,
                pipeline_fn=pipeline_fn,
                format_fn=format_result,
            )
        )

        await app.updater.start_polling(drop_pending_updates=True)

        try:
            await asyncio.Event().wait()  # run forever
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
        finally:
            queue_task.cancel()
            await app.updater.stop()
            await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
