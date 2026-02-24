"""Summarize collected messages using a configurable LLM provider.

Flow:
    1. Flatten messages from all channels into a numbered list
    2. Classify into NEWS / MACRO / STOCK / OTHER  (1 API call)
    3. Summarize each non-empty category             (up to 3 API calls)
    4. Build final telegram-formatted output
"""

import json
import logging
from datetime import datetime

from src.providers import LLMProvider, get_provider

logger = logging.getLogger(__name__)

DEFAULT_MODELS: dict[str, str] = {
    "claude": "claude-sonnet-4-5-20250929",
    "openai": "gpt-4o",
    "gemini": "gemini-2.0-flash",
}

CATEGORIES = ["NEWS", "MACRO", "STOCK", "OTHER"]


# ────────────────────────────────────────────────────────────
# 내부 헬퍼
# ────────────────────────────────────────────────────────────

def _flatten_messages(channel_messages: dict[str, list[dict]]) -> list[dict]:
    """Flatten all channel messages into a single numbered list."""
    flat = []
    idx = 1
    for channel_name, messages in channel_messages.items():
        for msg in messages:
            flat.append({
                "id": idx,
                "channel": channel_name,
                "date": msg["date"][:16],
                "text": msg["text"][:500],
                "url": msg.get("url", ""),
            })
            idx += 1
    return flat


def _format_messages_for_summary(messages: list[dict]) -> str:
    """Format messages for a summary prompt."""
    lines = []
    for msg in messages:
        url_part = f" ({msg['url']})" if msg.get("url") else ""
        lines.append(f"- [{msg['date']}][{msg['channel']}]{url_part} {msg['text']}")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────
# 1단계: 분류
# ────────────────────────────────────────────────────────────

def _classify_messages(
    flat_messages: list[dict],
    llm: LLMProvider,
    model: str,
    max_tokens: int = 2048,
) -> dict[str, list[dict]]:
    """Classify messages into NEWS/MACRO/STOCK/OTHER via LLM."""
    msg_list = "\n".join(
        f'{m["id"]}. [{m["channel"]}] {m["text"][:200]}'
        for m in flat_messages
    )

    prompt = f"""아래 메시지 목록을 각각 분류해서 JSON 배열로 반환해.
분류 기준:
- NEWS: 뉴스, 공시, 경제지표 발표, 보도자료
- MACRO: 시황, 지수(코스피/나스닥 등), 환율, 금리, 매크로 분석
- STOCK: 특정 종목 언급, 매수/매도 의견, 목표가, 실적
- OTHER: 광고, 잡담, 투자와 무관한 내용

메시지 목록:
{msg_list}

반환 형식 (반드시 JSON만 반환, 설명 없이):
[
  {{"id": 1, "category": "STOCK"}},
  {{"id": 2, "category": "MACRO"}},
  ...
]

카테고리가 복수인 경우 가장 주된 것 하나만 선택."""

    logger.info("Classifying %d messages...", len(flat_messages))
    response = llm.generate(prompt=prompt, model=model, max_tokens=max_tokens)
    logger.debug("Classification raw response: %s", response[:300])

    try:
        # 마크다운 코드블록 제거 (```json ... ```)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:])
        if cleaned.endswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[:-1])
        cleaned = cleaned.strip()

        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON array found in response: {response[:200]}")
        classifications = json.loads(cleaned[start:end])
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse classification JSON: %s. Falling back to OTHER.", e)
        classifications = [{"id": m["id"], "category": "OTHER"} for m in flat_messages]

    id_to_category = {item["id"]: item.get("category", "OTHER") for item in classifications}

    grouped: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
    for msg in flat_messages:
        category = id_to_category.get(msg["id"], "OTHER")
        if category not in grouped:
            category = "OTHER"
        grouped[category].append(msg)

    for cat, msgs in grouped.items():
        if msgs:
            logger.info("  %s: %d messages", cat, len(msgs))

    return grouped


# ────────────────────────────────────────────────────────────
# 2단계: 카테고리별 요약
# ────────────────────────────────────────────────────────────

def _summarize_news(messages: list[dict], llm: LLMProvider, model: str, max_tokens: int) -> str:
    formatted = _format_messages_for_summary(messages)
    prompt = f"""아래는 주식 관련 뉴스/공시 메시지 모음이야.
채널 구분 없이 투자에 영향을 줄 수 있는 내용만 추출해서 아래 형식으로 정리해줘.
- 각 뉴스 항목은 정확히 2줄로 요약할 것 (1줄: 핵심 내용, 2줄: 세부 수치/배경)
- 수치, 날짜, 시간 정보가 있으면 반드시 포함
- 중복되는 내용은 하나로 합칠 것. 중복 숫자를 괄호안에 추가해줘
- 중요도 순으로 정렬
- URL이 있으면 항목 끝에 반드시 포함

형식:
• [핵심 내용 1줄]
  [세부 수치/배경 1줄] | URL

{formatted}"""
    return llm.generate(prompt=prompt, model=model, max_tokens=max_tokens)


def _summarize_macro(messages: list[dict], llm: LLMProvider, model: str, max_tokens: int) -> str:
    formatted = _format_messages_for_summary(messages)
    prompt = f"""아래는 시황/매크로 관련 메시지 모음이야.
다음 순서로 정리해줘.
1. 전체 시장 방향성을 한 줄로 (강세 / 약세 / 혼조)
2. 주요 지수/환율/금리 수치 변화 (있는 것만)
3. 주목할 매크로 이슈
- 수치는 반드시 포함, 없으면 방향성(상승/하락)만이라도 표기
형식:
[방향성] ...
- 지수/환율/금리: ...
- 주요 이슈: ...

{formatted}"""
    return llm.generate(prompt=prompt, model=model, max_tokens=max_tokens)


def _summarize_stock(messages: list[dict], llm: LLMProvider, model: str, max_tokens: int) -> str:
    formatted = _format_messages_for_summary(messages)
    prompt = f"""아래는 종목 분석/언급 메시지 모음이야.
언급된 종목을 추출해서 아래 형식으로 정리해줘.
- 같은 종목이 여러 번 언급된 경우 하나로 합칠 것
- 언급된 숫자를 괄호안에 넣어 표기할 것
- 목표가/현재가 수치가 있으면 포함
- 긍정/부정/중립 판단은 메시지 내용 기준으로
형식:
📈 긍정
- 종목명 | 핵심 근거
📉 부정/주의
- 종목명 | 핵심 근거
⚪ 중립/정보
- 종목명 | 핵심 근거

{formatted}"""
    return llm.generate(prompt=prompt, model=model, max_tokens=max_tokens)


# ────────────────────────────────────────────────────────────
# 3단계: 최종 포맷
# ────────────────────────────────────────────────────────────

def _build_final_output(
    news_summary: str | None,
    macro_summary: str | None,
    stock_summary: str | None,
) -> str:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    hour_str = now.strftime("%H")
    divider = "━━━━━━━━━━━━━━━━━━━━"

    sections = []
    if news_summary:
        sections.append(f"📰 뉴스/공시\n{news_summary}")
    if macro_summary:
        sections.append(f"🌐 시황/매크로\n{macro_summary}")
    if stock_summary:
        sections.append(f"🔍 종목 분석\n{stock_summary}")

    if not sections:
        return ""

    body = f"\n\n{divider}\n\n".join(sections)

    return (
        f"{divider}\n"
        f"📊 마켓 요약 | {date_str} {hour_str}:00\n"
        f"{divider}\n\n"
        f"{body}\n\n"
        f"{divider}"
    )


# ────────────────────────────────────────────────────────────
# 퍼블릭 인터페이스
# ────────────────────────────────────────────────────────────

def summarize(
    channel_messages: dict[str, list[dict]],
    provider: str = "claude",
    model: str | None = None,
    max_tokens: int = 4096,
    language: str = "ko",
) -> str | None:
    """Classify and summarize messages by category.

    Args:
        channel_messages: Dict of channel name -> list of message dicts.
        provider: LLM provider name ("claude", "openai", "gemini").
        model: Model ID. If None, uses provider default.
        max_tokens: Max tokens per summary response.
        language: Unused (prompts are Korean by default).

    Returns:
        Formatted summary string, or None if no messages.
    """
    flat_messages = _flatten_messages(channel_messages)
    if not flat_messages:
        logger.info("No messages to summarize.")
        return None

    if model is None:
        model = DEFAULT_MODELS.get(provider, "")

    llm: LLMProvider = get_provider(provider)

    # 1단계: 분류
    grouped = _classify_messages(flat_messages, llm, model, max_tokens=2048)

    # 2단계: 카테고리별 요약
    news_summary = None
    macro_summary = None
    stock_summary = None

    if grouped["NEWS"]:
        logger.info("Summarizing NEWS (%d messages)...", len(grouped["NEWS"]))
        news_summary = _summarize_news(grouped["NEWS"], llm, model, max_tokens)

    if grouped["MACRO"]:
        logger.info("Summarizing MACRO (%d messages)...", len(grouped["MACRO"]))
        macro_summary = _summarize_macro(grouped["MACRO"], llm, model, max_tokens)

    if grouped["STOCK"]:
        logger.info("Summarizing STOCK (%d messages)...", len(grouped["STOCK"]))
        stock_summary = _summarize_stock(grouped["STOCK"], llm, model, max_tokens)

    # 3단계: 최종 포맷
    result = _build_final_output(news_summary, macro_summary, stock_summary)
    if result:
        logger.info("Summary generated (%d chars).", len(result))
        return result

    logger.info("No summarizable content (all OTHER).")
    return None
