"""Background processing of a GitHub pull-request review."""

from __future__ import annotations

import logging

from ..config import Settings
from ..core.diff import changed_paths, parse_diff
from ..core.models import ReviewRequest
from ..core.orchestrator import review as run_review
from ..llm.base import LLMClient
from ..vcs.github import GitHubClient

log = logging.getLogger("janett.github")


async def process_pull_request(
    *,
    settings: Settings,
    llm: LLMClient,
    installation_id: int,
    owner: str,
    repo: str,
    number: int,
    head_sha: str,
    title: str | None = None,
    body: str | None = None,
) -> None:
    """Fetch the PR diff, run the review, and post comments back."""
    client = GitHubClient(settings, installation_id)
    try:
        diff = await client.get_pr_diff(owner, repo, number)
        files = parse_diff(diff)
        # The orchestrator is the single authority on the too-many-files
        # guardrail: it declines the review when there are more than max_files.
        # Skip the (potentially large) content fetch when we know it will.
        if len(files) > settings.max_files:
            file_contents: dict[str, str] = {}
        else:
            file_contents = await client.get_file_contents(
                owner, repo, changed_paths(files),
                ref=head_sha, max_bytes=settings.max_file_bytes,
            )

        request = ReviewRequest(
            diff=diff,
            file_contents=file_contents,
            title=title,
            description=body,
        )
        result = await run_review(request, llm, settings)
        await client.post_review(owner, repo, number, head_sha, result)
        log.info(
            "Reviewed %s/%s#%s: %d finding(s)",
            owner, repo, number, len(result.findings),
        )
    except Exception:  # noqa: BLE001 — background task must not crash silently
        log.exception("Failed to review %s/%s#%s", owner, repo, number)
