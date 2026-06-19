"""GitHub webhook endpoint: verify, ack fast, review in the background."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from .tasks import process_pull_request

router = APIRouter()

# PR actions worth reviewing.
_REVIEW_ACTIONS = {"opened", "synchronize", "reopened", "ready_for_review"}


def _verify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str | None = Header(default=None),
) -> dict:
    settings = request.app.state.settings
    if not settings.github_configured:
        raise HTTPException(503, "GitHub App not configured")

    raw = await request.body()
    if not _verify_signature(settings.github_webhook_secret, raw, x_hub_signature_256):
        raise HTTPException(401, "Invalid signature")

    if x_github_event == "ping":
        return {"ok": True, "pong": True}
    if x_github_event != "pull_request":
        return {"ok": True, "ignored": x_github_event}

    payload = await request.json()
    action = payload.get("action")
    if action not in _REVIEW_ACTIONS:
        return {"ok": True, "ignored_action": action}

    pr = payload["pull_request"]
    if pr.get("draft") and action != "ready_for_review":
        return {"ok": True, "ignored": "draft"}

    repo = payload["repository"]
    owner = repo["owner"]["login"]
    repo_name = repo["name"]

    background_tasks.add_task(
        process_pull_request,
        settings=settings,
        llm=request.app.state.llm,
        installation_id=payload["installation"]["id"],
        owner=owner,
        repo=repo_name,
        number=pr["number"],
        head_sha=pr["head"]["sha"],
        title=pr.get("title"),
        body=pr.get("body"),
    )
    return {"ok": True, "queued": f"{owner}/{repo_name}#{pr['number']}"}
