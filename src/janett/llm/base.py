"""The LLM client interface the review engine depends on."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Minimal chat interface. Implementations: Ollama (default), OpenAI-compat."""

    #: Human-readable model identifier, recorded on the review result.
    model: str

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        schema: dict | None = None,
        temperature: float = 0.1,
    ) -> str:
        """Return the assistant's reply as a string.

        If ``schema`` is given, the implementation should request structured
        JSON output matching that schema (best effort).
        """
        ...
