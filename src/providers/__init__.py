"""Base class for LLM providers."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base for all LLM summarization providers."""

    @abstractmethod
    def generate(self, prompt: str, model: str, max_tokens: int) -> str:
        """Send a prompt and return the generated text.

        Args:
            prompt: The user prompt to send.
            model: Model identifier (provider-specific).
            max_tokens: Maximum tokens for the response.

        Returns:
            The generated text.
        """


def get_provider(provider_name: str) -> LLMProvider:
    """Factory that returns the right LLMProvider instance.

    Args:
        provider_name: One of "claude", "openai", "gemini".

    Raises:
        ValueError: If the provider name is unknown.
        ImportError: If the required SDK is not installed.
    """
    name = provider_name.lower()

    if name == "claude":
        from src.providers.claude import ClaudeProvider
        return ClaudeProvider()

    if name == "openai":
        from src.providers.openai import OpenAIProvider
        return OpenAIProvider()

    if name == "gemini":
        from src.providers.gemini import GeminiProvider
        return GeminiProvider()

    raise ValueError(
        f"Unknown provider '{provider_name}'. "
        "Supported: claude, openai, gemini"
    )
