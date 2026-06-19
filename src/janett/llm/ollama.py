"""Ollama chat client — the default backend.

Uses Ollama's native /api/chat endpoint with structured outputs (`format` set
to a JSON schema) so findings come back as valid JSON.
See https://ollama.com/blog/structured-outputs
"""

from __future__ import annotations

import httpx

from ._http import post_json_with_retry


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 300.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._timeout = timeout

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        schema: dict | None = None,
        temperature: float = 0.1,
    ) -> str:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if schema is not None:
            payload["format"] = schema

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            data = await post_json_with_retry(
                client, f"{self.base_url}/api/chat", json=payload
            )
        return data.get("message", {}).get("content", "")
