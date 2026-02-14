"""Summarize collected messages using Claude API."""

import logging
import os

import anthropic

logger = logging.getLogger(__name__)


def _build_prompt(channel_messages: dict[str, list[dict]], language: str) -> str:
    """Build the summarization prompt from collected messages."""
    sections = []
    for channel_name, messages in channel_messages.items():
        if not messages:
            continue
        lines = []
        for msg in messages:
            date = msg["date"][:10]
            url = msg.get("url", "")
            url_part = f" ({url})" if url else ""
            lines.append(f"- [{date}]{url_part} {msg['text'][:500]}")
        sections.append(f"## {channel_name}\n" + "\n".join(lines))

    if not sections:
        return ""

    lang_instruction = {
        "ko": "한국어로 작성해주세요.",
        "en": "Write in English.",
    }.get(language, f"Write in {language}.")

    return f"""\
아래는 여러 Telegram 채널에서 수집된 최신 메시지들입니다.
각 채널별로 핵심 내용을 요약하고, 중요한 뉴스나 인사이트를 정리해주세요.

요약 형식:
1. 각 채널별로 섹션을 나눠서 요약
2. 각 항목은 핵심 포인트 위주로 간결하게 정리
3. 중요도가 높은 내용은 별도로 강조
4. 원본 링크가 있으면 포함
5. {lang_instruction}

---

{chr(10).join(sections)}"""


def summarize(
    channel_messages: dict[str, list[dict]],
    model: str = "claude-sonnet-4-5-20250929",
    max_tokens: int = 4096,
    language: str = "ko",
) -> str | None:
    """Summarize messages using Claude API.

    Args:
        channel_messages: Dict of channel name -> list of message dicts.
        model: Claude model ID to use.
        max_tokens: Maximum tokens for the response.
        language: Language code for the summary.

    Returns:
        The summary text, or None if there are no messages to summarize.
    """
    prompt = _build_prompt(channel_messages, language)
    if not prompt:
        logger.info("No messages to summarize.")
        return None

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    logger.info("Requesting summary from Claude (%s)...", model)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )

    summary = response.content[0].text
    logger.info("Summary generated (%d chars).", len(summary))
    return summary
