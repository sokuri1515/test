"""Periodic scheduler for the summarization pipeline."""

import asyncio
import logging

from telethon import TelegramClient

from src.reader import fetch_new_messages
from src.sender import save_markdown, send_telegram
from src.summarizer import summarize

logger = logging.getLogger(__name__)


async def run_cycle(
    user_client: TelegramClient,
    bot_client: TelegramClient,
    config: dict,
) -> None:
    """Execute one summarization cycle.

    1. Fetch new messages from all configured channels
    2. Summarize them with Claude
    3. Send the summary via configured outputs
    """
    channels = config["channels"]
    schedule_cfg = config["schedule"]
    summarizer_cfg = config["summarizer"]
    output_cfg = config["output"]

    # Step 1: Fetch messages
    logger.info("--- Starting summarization cycle ---")
    channel_messages = await fetch_new_messages(
        client=user_client,
        channels=channels,
        max_messages=schedule_cfg.get("max_messages_per_channel", 50),
    )

    total = sum(len(msgs) for msgs in channel_messages.values())
    if total == 0:
        logger.info("No new messages found. Skipping this cycle.")
        return

    logger.info("Total new messages collected: %d", total)

    # Step 2: Summarize
    summary = summarize(
        channel_messages=channel_messages,
        provider=summarizer_cfg.get("provider", "claude"),
        model=summarizer_cfg.get("model"),
        max_tokens=summarizer_cfg.get("max_tokens", 4096),
        language=summarizer_cfg.get("language", "ko"),
    )

    if not summary:
        logger.warning("Summarizer returned empty result.")
        return

    # Step 3: Output
    if output_cfg.get("telegram", True):
        await send_telegram(bot_client, summary)

    if output_cfg.get("markdown", False):
        save_markdown(summary, output_cfg.get("markdown_dir", "summaries"))

    logger.info("--- Summarization cycle complete ---")


async def start_scheduler(
    user_client: TelegramClient,
    bot_client: TelegramClient,
    config: dict,
) -> None:
    """Run summarization cycles at the configured interval."""
    interval = config["schedule"].get("interval_minutes", 60)
    logger.info("Scheduler started. Interval: %d minutes.", interval)

    # Run the first cycle immediately
    await run_cycle(user_client, bot_client, config)

    # Then loop at the configured interval
    while True:
        logger.info("Next cycle in %d minutes...", interval)
        await asyncio.sleep(interval * 60)
        await run_cycle(user_client, bot_client, config)
