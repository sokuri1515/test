"""Claude (Anthropic) provider."""

import os

import anthropic

from src.providers import LLMProvider


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def generate(self, prompt: str, model: str, max_tokens: int) -> str:
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
