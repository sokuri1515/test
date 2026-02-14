"""Send summaries via Telegram Bot API."""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from telethon import TelegramClient
from telethon.types import Message

logger = logging.getLogger(__name__)

# Telegram message limit is 4096 characters
MAX_MESSAGE_LENGTH = 4096


def _split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break

        # Find the last newline within the limit
        split_pos = text.rfind("\n", 0, max_length)
        if split_pos == -1:
            # No newline found; split at max_length
            split_pos = max_length

        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")

    return chunks


async def send_telegram(
    client: TelegramClient,
    summary: str,
    chat_id: str | int | None = None,
) -> list[Message]:
    """Send a summary to a Telegram chat using the bot client.

    Args:
        client: An authenticated TelegramClient (bot).
        summary: The summary text to send.
        chat_id: Target chat ID. Defaults to TELEGRAM_CHAT_ID env var.

    Returns:
        List of sent Message objects.
    """
    if chat_id is None:
        chat_id = os.environ["TELEGRAM_CHAT_ID"]

    # Convert numeric string to int
    if isinstance(chat_id, str) and chat_id.lstrip("-").isdigit():
        chat_id = int(chat_id)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = f"📋 **Telegram Channel Summary**\n🕐 {now}\n\n"
    full_text = header + summary

    chunks = _split_message(full_text)
    sent_messages = []

    for i, chunk in enumerate(chunks):
        if i > 0:
            chunk = f"(continued {i + 1}/{len(chunks)})\n\n{chunk}"
        msg = await client.send_message(chat_id, chunk, parse_mode="md")
        sent_messages.append(msg)
        logger.info("Sent summary chunk %d/%d to chat %s", i + 1, len(chunks), chat_id)

    return sent_messages


def save_markdown(summary: str, output_dir: str = "summaries") -> Path:
    """Save a summary as a markdown file.

    Args:
        summary: The summary text.
        output_dir: Directory to save the file in.

    Returns:
        Path to the saved file.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    filename = now.strftime("%Y-%m-%d_%H%M") + "_summary.md"
    filepath = out_path / filename

    content = f"---\ndate: {now.isoformat()}\ntype: telegram-summary\n---\n\n{summary}\n"
    filepath.write_text(content, encoding="utf-8")

    logger.info("Summary saved to %s", filepath)
    return filepath
