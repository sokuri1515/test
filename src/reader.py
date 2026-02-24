"""Telegram channel message reader using Telethon."""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
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
    hours_back: int = 4,
) -> dict[str, list[dict]]:
    """Fetch new messages from the configured channels.

    Args:
        client: An authenticated TelegramClient instance.
        channels: List of channel usernames or IDs to read from.
        max_messages: Maximum messages to fetch per channel.
        hours_back: When no prior state exists, fetch messages from this many hours ago.

    Returns:
        A dict mapping channel name to a list of message dicts.
    """
    state = _load_state()
    result: dict[str, list[dict]] = {}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    for channel in channels:
        channel_key = str(channel)
        min_id = state.get(channel_key, 0)
        messages: list[dict] = []

        try:
            entity = await client.get_entity(channel)
            channel_title = getattr(entity, "title", channel_key)

            if min_id == 0:
                # 첫 실행: 최신순으로 가져와서 cutoff 이후 메시지만 수집
                async for msg in client.iter_messages(entity, limit=max_messages):
                    if not msg.text:
                        continue
                    if msg.date < cutoff:
                        break  # 최신순 순회 중 cutoff보다 오래된 메시지 만나면 중단
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
                messages.reverse()  # 시간순 정렬
            else:
                # 이후 실행: 마지막 ID 이후 메시지 수집
                async for msg in client.iter_messages(
                    entity, limit=max_messages, min_id=min_id, reverse=True
                ):
                    if not msg.text:
                        continue
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
