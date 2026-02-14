"""Telegram channel message reader using Telethon."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from telethon import TelegramClient

logger = logging.getLogger(__name__)

STATE_FILE = Path("data/reader_state.json")


def _load_state() -> dict:
    """Load the last-read message IDs per channel."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_state(state: dict) -> None:
    """Persist the last-read message IDs per channel."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


async def fetch_new_messages(
    client: TelegramClient,
    channels: list[str],
    max_messages: int = 50,
) -> dict[str, list[dict]]:
    """Fetch new messages from the configured channels.

    Args:
        client: An authenticated TelegramClient instance.
        channels: List of channel usernames or IDs to read from.
        max_messages: Maximum messages to fetch per channel.

    Returns:
        A dict mapping channel name to a list of message dicts.
    """
    state = _load_state()
    result: dict[str, list[dict]] = {}

    for channel in channels:
        channel_key = str(channel)
        min_id = state.get(channel_key, 0)
        messages: list[dict] = []

        try:
            entity = await client.get_entity(channel)
            channel_title = getattr(entity, "title", channel_key)

            async for msg in client.iter_messages(
                entity,
                limit=max_messages,
                min_id=min_id,
                reverse=True,
            ):
                if msg.text:
                    messages.append(
                        {
                            "id": msg.id,
                            "date": msg.date.isoformat(),
                            "text": msg.text,
                            "url": f"https://t.me/{channel_key}/{msg.id}"
                            if isinstance(channel, str)
                            else None,
                        }
                    )

            if messages:
                state[channel_key] = messages[-1]["id"]
                logger.info(
                    "Fetched %d new messages from [%s]",
                    len(messages),
                    channel_title,
                )
            else:
                logger.info("No new messages from [%s]", channel_title)

            result[channel_title] = messages

        except Exception:
            logger.exception("Failed to fetch messages from %s", channel_key)
            result[channel_key] = []

    _save_state(state)
    return result


def create_client() -> TelegramClient:
    """Create a TelegramClient from environment variables."""
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]

    Path("data").mkdir(parents=True, exist_ok=True)
    return TelegramClient("data/telegram_session", api_id, api_hash)
