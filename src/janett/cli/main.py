"""Janett local CLI — review a local git diff with Ollama (or any backend).

Examples:
    janett review                  # working tree vs HEAD
    janett review --staged         # staged changes
    janett review --base main      # main..HEAD
    janett review --remote https://my-janett.up.railway.app
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import typer
from rich.console import Console

from ..config import get_settings
from ..core.models import ReviewRequest, ReviewResult
from ..core.orchestrator import review as run_review
from ..llm.factory import build_llm_client
from ..vcs.local import build_request_from_git
from .render import render_result

app = typer.Typer(add_completion=False, help="Janett — AI code review bot")
console = Console()


@app.callback()
def _root() -> None:
    """Janett — AI code review bot.

    The callback keeps `review` a named subcommand (Typer otherwise collapses a
    single-command app into the root, breaking the documented `janett review`).
    """


def _review_remote(request: ReviewRequest, remote: str) -> ReviewResult:
    url = remote.rstrip("/") + "/review"
    resp = httpx.post(url, json=request.model_dump(mode="json"), timeout=600)
    resp.raise_for_status()
    return ReviewResult.model_validate(resp.json())


async def _review_local(request: ReviewRequest) -> ReviewResult:
    settings = get_settings()
    llm = build_llm_client(settings)
    return await run_review(request, llm, settings)


@app.command()
def review(
    base: str = typer.Option(None, "--base", "-b", help="Base ref (e.g. main); reviews base...head"),
    head: str = typer.Option("HEAD", "--head", "-h", help="Head ref"),
    staged: bool = typer.Option(False, "--staged", help="Review staged changes"),
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Path to the git repo"),
    remote: str = typer.Option(None, "--remote", help="URL of a deployed Janett API to use instead of local LLM"),
    fail_on_error: bool = typer.Option(True, help="Exit non-zero if any error-severity findings"),
) -> None:
    """Review local changes and print findings."""
    settings = get_settings()
    request = build_request_from_git(
        repo=repo, base=base, head=head, staged=staged, settings=settings
    )

    if not request.diff.strip():
        console.print("[dim]No changes to review.[/dim]")
        raise typer.Exit(0)

    try:
        if remote:
            result = _review_remote(request, remote)
        else:
            result = asyncio.run(_review_local(request))
    except httpx.HTTPError as exc:
        console.print(f"[red]Request failed:[/red] {exc}")
        raise typer.Exit(2)

    render_result(result, console)

    if fail_on_error and result.has_errors:
        raise typer.Exit(1)


def main() -> None:  # console-script friendly entry point
    app()


if __name__ == "__main__":
    main()
