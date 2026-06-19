"""Synchronous review endpoint — used by the CLI's --remote mode and ad-hoc calls."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..core.models import ReviewRequest, ReviewResult
from ..core.orchestrator import review as run_review

router = APIRouter()


@router.post("/review", response_model=ReviewResult)
async def review_endpoint(request: ReviewRequest, http_request: Request) -> ReviewResult:
    settings = http_request.app.state.settings
    llm = http_request.app.state.llm
    return await run_review(request, llm, settings)
