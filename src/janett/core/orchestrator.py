"""The review engine — transport-agnostic.

`review()` is the single entry point used by the CLI, the API, and the GitHub
background task. It knows nothing about HTTP, git, or GitHub.
"""

from __future__ import annotations

from ..config import Settings, get_settings
from ..llm.base import LLMClient
from .diff import parse_diff
from .findings import output_json_schema, parse_review_output
from .models import ReviewRequest, ReviewResult
from .prompt import build_messages


async def review(
    request: ReviewRequest,
    llm: LLMClient,
    settings: Settings | None = None,
) -> ReviewResult:
    """Review a diff and return structured findings."""
    settings = settings or get_settings()

    if len(request.diff.encode("utf-8")) > settings.max_diff_bytes:
        return ReviewResult(skipped_reason="diff too large", model=llm.model)

    files = parse_diff(request.diff)
    if not files:
        return ReviewResult(summary="No reviewable changes.", model=llm.model)
    if len(files) > settings.max_files:
        return ReviewResult(skipped_reason="too many files changed", model=llm.model)

    messages = build_messages(request, files)
    raw = await llm.chat(
        messages,
        schema=output_json_schema(),
        temperature=settings.llm_temperature,
    )

    result = parse_review_output(raw, files)
    result.model = llm.model
    return result
