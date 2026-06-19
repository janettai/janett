"""Local git source: build a ReviewRequest from a working copy."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..config import Settings, get_settings
from ..core.diff import changed_paths, parse_diff
from ..core.models import ReviewRequest


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def build_request_from_git(
    repo: Path,
    base: str | None = None,
    head: str = "HEAD",
    staged: bool = False,
    settings: Settings | None = None,
) -> ReviewRequest:
    """Produce a ReviewRequest from a local git repo.

    - ``staged``: review staged changes (``git diff --cached``).
    - ``base`` given: review ``base..head``.
    - otherwise: review the working tree against ``head``.
    """
    settings = settings or get_settings()

    if staged:
        diff = _git(repo, "diff", "--cached", "--unified=3")
    elif base:
        diff = _git(repo, "diff", f"{base}..{head}", "--unified=3")
    else:
        diff = _git(repo, "diff", head, "--unified=3")

    files = parse_diff(diff)
    file_contents: dict[str, str] = {}
    for path in changed_paths(files):
        full = repo / path
        try:
            data = full.read_bytes()
        except OSError:
            continue
        if len(data) > settings.max_file_bytes:
            continue
        try:
            file_contents[path] = data.decode("utf-8")
        except UnicodeDecodeError:
            continue  # skip binary-ish files

    return ReviewRequest(diff=diff, file_contents=file_contents)
