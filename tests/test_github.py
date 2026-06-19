"""GitHub review posting — the 422 inline-comment fallback."""

import json

import httpx

import janett.vcs.github as gh
from janett.config import Settings
from janett.core.models import Finding, ReviewResult, Severity


def _result() -> ReviewResult:
    return ReviewResult(
        summary="found stuff",
        findings=[
            Finding(
                path="a.py",
                line=2,
                severity=Severity.error,
                category="bug",
                message="div by zero",
            )
        ],
    )


def test_fallback_body_inlines_findings():
    body = gh._fallback_body(_result())
    assert "found stuff" in body
    assert "a.py:2" in body
    assert "div by zero" in body


def _patch_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(
        gh.httpx,
        "AsyncClient",
        lambda *a, **k: real(*a, **{**k, "transport": transport}),
    )

    async def fake_ensure(self, client):  # skip JWT/token exchange
        return "t"

    monkeypatch.setattr(gh.GitHubClient, "_ensure_token", fake_ensure)


async def test_post_review_falls_back_when_inline_rejected(monkeypatch):
    posts = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        posts.append(payload)
        if payload.get("comments"):
            return httpx.Response(422, json={"message": "line not part of diff"})
        return httpx.Response(200, json={"id": 1})

    _patch_transport(monkeypatch, handler)

    client = gh.GitHubClient(Settings(), installation_id=1)
    await client.post_review("o", "r", 5, "sha", _result())

    assert len(posts) == 2  # initial (with comments) + fallback (without)
    assert posts[0]["comments"]  # first attempt anchored inline comments
    assert not posts[1].get("comments")  # fallback dropped them
    assert "div by zero" in posts[1]["body"]  # ...but findings survive in body


async def test_post_review_does_not_fall_back_on_success(monkeypatch):
    posts = []

    def handler(request: httpx.Request) -> httpx.Response:
        posts.append(json.loads(request.content))
        return httpx.Response(200, json={"id": 1})

    _patch_transport(monkeypatch, handler)

    client = gh.GitHubClient(Settings(), installation_id=1)
    await client.post_review("o", "r", 5, "sha", _result())

    assert len(posts) == 1  # single post, no fallback
    assert posts[0]["comments"]
