"""GitHub App adapter: authenticate, fetch a PR's diff, post a review.

Uses httpx directly against the REST API. Auth is the standard GitHub App flow:
a short-lived JWT signed with the App private key is exchanged for an
installation access token, which is then used for repo calls.
"""

from __future__ import annotations

import asyncio
import time

import httpx
import jwt

from ..config import Settings
from ..core.models import Finding, ReviewResult, Severity

_API = "https://api.github.com"
_DIFF_ACCEPT = "application/vnd.github.v3.diff"
_JSON_ACCEPT = "application/vnd.github+json"

_SEVERITY_EMOJI = {
    Severity.error: "🔴",
    Severity.warning: "🟡",
    Severity.info: "🔵",
}


def _app_jwt(settings: Settings) -> str:
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 9 * 60, "iss": settings.github_app_id}
    return jwt.encode(payload, settings.normalized_private_key, algorithm="RS256")


class GitHubClient:
    def __init__(self, settings: Settings, installation_id: int) -> None:
        self._settings = settings
        self._installation_id = installation_id
        self._token: str | None = None

    async def _ensure_token(self, client: httpx.AsyncClient) -> str:
        if self._token:
            return self._token
        resp = await client.post(
            f"{_API}/app/installations/{self._installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {_app_jwt(self._settings)}",
                "Accept": _JSON_ACCEPT,
            },
        )
        resp.raise_for_status()
        self._token = resp.json()["token"]
        return self._token

    async def _auth_headers(self, client: httpx.AsyncClient, accept: str) -> dict:
        token = await self._ensure_token(client)
        return {"Authorization": f"Bearer {token}", "Accept": accept}

    async def get_pr_diff(self, owner: str, repo: str, number: int) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            headers = await self._auth_headers(client, _DIFF_ACCEPT)
            resp = await client.get(
                f"{_API}/repos/{owner}/{repo}/pulls/{number}", headers=headers
            )
            resp.raise_for_status()
            return resp.text

    async def get_file_contents(
        self, owner: str, repo: str, paths: list[str], ref: str, max_bytes: int
    ) -> dict[str, str]:
        contents: dict[str, str] = {}
        # Bound concurrency so a large PR doesn't fire dozens of requests at once.
        semaphore = asyncio.Semaphore(8)

        async with httpx.AsyncClient(timeout=60) as client:
            headers = await self._auth_headers(client, "application/vnd.github.raw")

            async def fetch(path: str) -> None:
                async with semaphore:
                    resp = await client.get(
                        f"{_API}/repos/{owner}/{repo}/contents/{path}",
                        headers=headers,
                        params={"ref": ref},
                    )
                if resp.status_code != 200 or len(resp.content) > max_bytes:
                    return
                try:
                    contents[path] = resp.content.decode("utf-8")
                except UnicodeDecodeError:
                    return

            await asyncio.gather(*(fetch(p) for p in paths))
        return contents

    async def post_review(
        self,
        owner: str,
        repo: str,
        number: int,
        commit_sha: str,
        result: ReviewResult,
    ) -> None:
        comments = [_to_comment(f) for f in result.findings]
        body = _review_body(result)
        # GitHub rejects a REQUEST_CHANGES/COMMENT review with zero comments only
        # if body is empty; we always include a summary body.
        payload = {
            "commit_id": commit_sha,
            "body": body,
            "event": "COMMENT",
            "comments": comments,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            headers = await self._auth_headers(client, _JSON_ACCEPT)
            resp = await client.post(
                f"{_API}/repos/{owner}/{repo}/pulls/{number}/reviews",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()


def _to_comment(finding: Finding) -> dict:
    emoji = _SEVERITY_EMOJI.get(finding.severity, "")
    body = f"{emoji} **{finding.severity.value}** ({finding.category}): {finding.message}"
    if finding.suggestion:
        body += f"\n\n```suggestion\n{finding.suggestion}\n```"
    return {
        "path": finding.path,
        "line": finding.line,
        "side": finding.side.value,
        "body": body,
    }


def _review_body(result: ReviewResult) -> str:
    if result.skipped_reason:
        return f"Janett skipped this review: {result.skipped_reason}."
    n = len(result.findings)
    head = result.summary or "Janett review complete."
    if n == 0:
        return f"{head}\n\n✅ No issues found."
    return f"{head}\n\n🔎 {n} finding(s) below."
