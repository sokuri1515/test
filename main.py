"""Telegram Channel Summarizer — Entry Point.

Reads messages from configured Telegram channels, summarizes them
using Claude API, and sends the summary via Telegram bot.

Usage:
    python main.py              # Run with scheduler (periodic)
    python main.py --once       # Run a single cycle and exit
"""

import argparse
import asyncio
import logging
import os
import sys

import yaml
from dotenv import load_dotenv
from telethon import TelegramClient

from src.reader import create_client
from src.scheduler import run_cycle, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_env() -> list[str]:
    """Check that all required environment variables are set."""
    required = [
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "ANTHROPIC_API_KEY",
    ]
    missing = [var for var in required if not os.environ.get(var)]
    return missing


def create_bot_client() -> TelegramClient:
    """Create a TelegramClient for the bot."""
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]

    client = TelegramClient("data/bot_session", api_id, api_hash)
    client._bot_token = bot_token
    return client


async def main(run_once: bool = False) -> None:
    """Main async entry point."""
    load_dotenv()

    missing = validate_env()
    if missing:
        logger.error(
            "Missing required environment variables: %s\n"
            "Copy .env.example to .env and fill in your credentials.",
            ", ".join(missing),
        )
        sys.exit(1)

    config = load_config()
    logger.info(
        "Loaded config: %d channels, scheduled hours: %s",
        len(config["channels"]),
        config["schedule"].get("scheduled_hours", []),
    )

    # Create clients
    user_client = create_client()
    bot_client = create_bot_client()

    bot_token = bot_client._bot_token
    await bot_client.start(bot_token=bot_token)

    async with user_client:
        # User client will prompt for phone/code on first run
        await user_client.start()

        logger.info("Both clients connected successfully.")

        if run_once:
            await run_cycle(user_client, bot_client, config)
        else:
            await start_scheduler(user_client, bot_client, config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Channel Summarizer")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single summarization cycle and exit",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(run_once=args.once))
    except KeyboardInterrupt:
        logger.info("Shutting down...")
