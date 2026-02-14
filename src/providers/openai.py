"""OpenAI (ChatGPT) provider."""

import os

from openai import OpenAI

from src.providers import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI ChatGPT API provider."""

    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def generate(self, prompt: str, model: str, max_tokens: int) -> str:
        response = self.client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
