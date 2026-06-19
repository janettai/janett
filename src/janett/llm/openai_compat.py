"""OpenAI-compatible chat client — used in production / for remote endpoints.

Works against the OpenAI API, against any OpenAI-compatible gateway, and against
a remote Ollama box (whose OpenAI-compatible API lives at <host>/v1).
"""

from __future__ import annotations

import httpx


class OpenAICompatClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 300.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key
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
            "temperature": temperature,
        }
        if schema is not None:
            # Ask for a JSON object. (Strict json_schema response_format is not
            # universally supported across compatible gateways, so we use the
            # widely-supported json_object mode and rely on the prompt + schema
            # described in the messages for shape.)
            payload["response_format"] = {"type": "json_object"}

        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]
