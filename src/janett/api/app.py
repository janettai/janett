"""FastAPI application: serves the review engine over HTTP."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..config import get_settings
from ..llm.factory import build_llm_client
from .routes_github import router as github_router
from .routes_review import router as review_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Build the LLM client once and share it across requests.
    app.state.settings = settings
    app.state.llm = build_llm_client(settings)
    yield


app = FastAPI(title="Janett", version="0.1.0", lifespan=lifespan)
app.include_router(review_router)
app.include_router(github_router)


@app.get("/health")
async def health() -> dict:
    settings = app.state.settings
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "model": app.state.llm.model,
        "github_configured": settings.github_configured,
    }
