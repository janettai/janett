"""Build the configured LLM client."""

from __future__ import annotations

from ..config import Settings, get_settings
from .base import LLMClient
from .ollama import OllamaClient
from .openai_compat import OpenAICompatClient


def build_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    if settings.llm_provider == "openai":
        return OpenAICompatClient(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout=settings.llm_timeout_seconds,
        )
    return OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.llm_timeout_seconds,
    )
