# Telegram Channel Summarizer

Telegram 채널의 메시지를 주기적으로 수집하고, Claude API로 요약한 뒤 Telegram Bot으로 전송하는 도구입니다.

## 동작 방식

```
Telegram 채널 → 메시지 수집 (Telethon) → 요약 (Claude API) → Telegram Bot 전송
```

## 사전 준비

### 1. API 자격증명 발급

| 항목 | 발급처 |
|------|--------|
| Telegram API ID / Hash | https://my.telegram.org |
| Telegram Bot Token | Telegram에서 @BotFather와 대화 |
| Anthropic API Key | https://console.anthropic.com |

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

## 설정

`config.yaml`에서 모니터링할 채널과 동작 옵션을 설정합니다:

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
│   ├── summarizer.py    # Claude API 요약 생성
│   ├── sender.py        # 요약 결과 전송 (Bot / Markdown)
│   └── scheduler.py     # 주기적 실행 관리
└── data/                # 세션 파일 및 상태 저장 (git 제외)
```

## 향후 계획

- [ ] 선택한 글을 Zettelkasten 형태의 Markdown으로 저장
- [ ] 키워드/주제 기반 필터링
- [ ] 웹 대시보드
