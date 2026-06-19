"""The shared LLM HTTP retry helper."""

import httpx
import pytest

from janett.llm._http import post_json_with_retry


async def test_retries_transient_status_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, json={"err": "busy"})
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        data = await post_json_with_retry(client, "http://x/api", json={}, backoff=0)

    assert data == {"ok": True}
    assert calls["n"] == 3  # two failures, then success


async def test_gives_up_after_retries_and_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await post_json_with_retry(
                client, "http://x/api", json={}, retries=1, backoff=0
            )


async def test_non_retryable_4xx_raises_immediately():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await post_json_with_retry(client, "http://x/api", json={}, backoff=0)

    assert calls["n"] == 1  # no retries on a 400


async def test_retries_connection_errors():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        data = await post_json_with_retry(client, "http://x/api", json={}, backoff=0)

    assert data == {"ok": True}
    assert calls["n"] == 2
