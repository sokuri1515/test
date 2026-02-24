"""Periodic scheduler for the summarization pipeline."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient

from src.reader import fetch_new_messages
from src.sender import save_markdown, send_telegram
from src.summarizer import summarize

logger = logging.getLogger(__name__)


def _seconds_until_next_run(scheduled_hours: list[int]) -> float:
    """Return seconds until the next scheduled run time."""
    now = datetime.now()
    today = now.date()

    candidates = []
    for hour in scheduled_hours:
        candidate = datetime(today.year, today.month, today.day, hour, 0, 0)
        if candidate <= now:
            candidate += timedelta(days=1)
        candidates.append(candidate)

    next_run = min(candidates)
    wait_seconds = (next_run - now).total_seconds()
    logger.info("Next scheduled run at %s (in %.0f minutes)", next_run.strftime("%H:%M"), wait_seconds / 60)
    return wait_seconds


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
        hours_back=schedule_cfg.get("hours_back", 4),
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
    """Run summarization cycles at fixed scheduled times."""
    scheduled_hours = config["schedule"].get("scheduled_hours", [4, 8, 12, 16, 20, 0])
    logger.info("Scheduler started. Scheduled hours: %s", scheduled_hours)

    while True:
        wait_seconds = _seconds_until_next_run(scheduled_hours)
        await asyncio.sleep(wait_seconds)
        await run_cycle(user_client, bot_client, config)
