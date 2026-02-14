# Telegram Channel Summarizer

Telegram 채널의 메시지를 주기적으로 수집하고, LLM API로 요약한 뒤 Telegram Bot으로 전송하는 도구입니다.

**지원 LLM**: Claude / ChatGPT / Gemini — `config.yaml`에서 한 줄로 교체 가능

## 동작 방식

```
Telegram 채널 → 메시지 수집 (Telethon) → 요약 (LLM) → Telegram Bot 전송
```

## 사전 준비

### 1. API 자격증명 발급

| 항목 | 발급처 |
|------|--------|
| Telegram API ID / Hash | https://my.telegram.org |
| Telegram Bot Token | Telegram에서 @BotFather와 대화 |
| Anthropic API Key | https://console.anthropic.com |
| OpenAI API Key | https://platform.openai.com/api-keys |
| Google Gemini API Key | https://aistudio.google.com/apikey |

> LLM API 키는 **사용할 provider의 것만** 있으면 됩니다.

### 2. Bot을 채팅방에 추가

요약을 받을 채팅방(개인 또는 그룹)에 생성한 봇을 추가하고, Chat ID를 확인합니다.
Chat ID 확인: Telegram에서 `@userinfobot` 또는 `@raw_data_bot`에게 메시지를 전송하세요.

## 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 입력
```

## LLM Provider 설정

`config.yaml`의 `summarizer.provider`를 변경하면 요약에 사용할 모델을 교체할 수 있습니다:

```yaml
# Claude 사용 (기본값)
summarizer:
  provider: "claude"
  model: null                        # 기본: claude-sonnet-4-5-20250929

# ChatGPT로 변경
summarizer:
  provider: "openai"
  model: null                        # 기본: gpt-4o
  # model: "gpt-4o-mini"             # 또는 특정 모델 지정

# Gemini로 변경
summarizer:
  provider: "gemini"
  model: null                        # 기본: gemini-2.0-flash
  # model: "gemini-2.5-pro-preview"  # 또는 특정 모델 지정
```

| Provider | 기본 모델 | 환경변수 |
|----------|-----------|----------|
| `claude` | `claude-sonnet-4-5-20250929` | `ANTHROPIC_API_KEY` |
| `openai` | `gpt-4o` | `OPENAI_API_KEY` |
| `gemini` | `gemini-2.0-flash` | `GEMINI_API_KEY` |

`model` 을 `null`로 두면 각 provider의 기본 모델이 사용됩니다. 특정 모델을 쓰고 싶으면 모델 ID를 직접 지정하세요.

## 채널 설정

`config.yaml`에서 모니터링할 채널을 설정합니다:

```yaml
channels:
  - channel_username_1
  - channel_username_2

schedule:
  interval_minutes: 60
  max_messages_per_channel: 50
```

## 실행

```bash
# 주기적 실행 (스케줄러 모드)
python main.py

# 1회 실행 후 종료
python main.py --once
```

첫 실행 시 Telegram 로그인(전화번호 + 인증코드)을 요청합니다. 이후 세션이 저장되어 자동 로그인됩니다.

## 프로젝트 구조

```
├── main.py              # 엔트리포인트
├── config.yaml          # 채널 목록 및 동작 설정
├── requirements.txt     # Python 의존성
├── .env.example         # 환경 변수 템플릿
├── src/
│   ├── reader.py        # Telegram 채널 메시지 수집
│   ├── summarizer.py    # LLM 요약 (provider 선택)
│   ├── sender.py        # 요약 결과 전송 (Bot / Markdown)
│   ├── scheduler.py     # 주기적 실행 관리
│   └── providers/       # LLM Provider 구현
│       ├── __init__.py  # 베이스 클래스 + 팩토리
│       ├── claude.py    # Anthropic Claude
│       ├── openai.py    # OpenAI ChatGPT
│       └── gemini.py    # Google Gemini
└── data/                # 세션 파일 및 상태 저장 (git 제외)
```

## 새 Provider 추가하기

1. `src/providers/`에 새 파일 생성 (예: `my_llm.py`)
2. `LLMProvider`를 상속하고 `generate()` 메서드 구현
3. `src/providers/__init__.py`의 `get_provider()`에 등록

```python
# src/providers/my_llm.py
from src.providers import LLMProvider

class MyLLMProvider(LLMProvider):
    def generate(self, prompt: str, model: str, max_tokens: int) -> str:
        # 여기에 API 호출 구현
        ...
```

## 향후 계획

- [ ] 선택한 글을 Zettelkasten 형태의 Markdown으로 저장
- [ ] 키워드/주제 기반 필터링
- [ ] 웹 대시보드
