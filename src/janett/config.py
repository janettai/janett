"""Application configuration, loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM backend -------------------------------------------------------
    # `ollama` is the default for local/dev. In production (e.g. Railway, which
    # has no GPU) set LLM_PROVIDER=openai and point OPENAI_BASE_URL at a remote
    # endpoint — that can be a hosted provider or a remote Ollama box, since
    # Ollama exposes an OpenAI-compatible API.
    llm_provider: Literal["ollama", "openai"] = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"

    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Shared LLM knobs
    llm_temperature: float = 0.1
    llm_timeout_seconds: float = 300.0

    # --- GitHub App --------------------------------------------------------
    github_app_id: str = ""
    # PEM contents (newlines may be encoded as literal "\n" in env vars).
    github_private_key: str = ""
    github_webhook_secret: str = ""

    # --- Review guardrails -------------------------------------------------
    max_diff_bytes: int = 400_000
    max_files: int = 60
    # Per-file content cap so huge files don't blow the context window.
    max_file_bytes: int = 60_000

    @property
    def normalized_private_key(self) -> str:
        """Return the PEM with real newlines (env vars often escape them)."""
        return self.github_private_key.replace("\\n", "\n")

    @property
    def github_configured(self) -> bool:
        return bool(
            self.github_app_id
            and self.github_private_key
            and self.github_webhook_secret
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
