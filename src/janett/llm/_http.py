"""Shared HTTP helper: POST JSON with bounded retries on transient failures.

LLM gateways (hosted providers, a remote Ollama box) routinely return the odd
429/5xx or drop a connection. A single such blip should not lose a whole review,
so we retry a few times with exponential backoff. Non-retryable responses (4xx
other than 429) propagate immediately.
"""

from __future__ import annotations

import asyncio

import httpx

# Status codes worth retrying: rate limiting and transient server/gateway errors.
_RETRY_STATUS = {429, 500, 502, 503, 504}


async def post_json_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    json: dict,
    headers: dict | None = None,
    retries: int = 2,
    backoff: float = 0.5,
) -> dict:
    """POST ``json`` and return the decoded response, retrying transient errors.

    Retries connection/timeout errors and retryable status codes up to
    ``retries`` times, sleeping ``backoff * 2**attempt`` between tries. Raises
    the last error if every attempt fails.
    """
    for attempt in range(retries + 1):
        try:
            resp = await client.post(url, json=json, headers=headers)
            if resp.status_code in _RETRY_STATUS and attempt < retries:
                await asyncio.sleep(backoff * 2**attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError:
            # Connection reset, DNS failure, read timeout, etc.
            if attempt < retries:
                await asyncio.sleep(backoff * 2**attempt)
                continue
            raise
    # Unreachable: the final attempt either returns or raises above.
    raise RuntimeError("post_json_with_retry exhausted retries without raising")
