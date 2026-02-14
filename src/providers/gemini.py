"""Google Gemini provider."""

import os

from google import genai

from src.providers import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def generate(self, prompt: str, model: str, max_tokens: int) -> str:
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                max_output_tokens=max_tokens,
            ),
        )
        return response.text
