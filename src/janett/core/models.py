"""Core data models shared by every front-end (CLI, API, GitHub).

These types are deliberately transport-agnostic: the review engine speaks only
in terms of a `ReviewRequest` and a `ReviewResult`.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"


class Side(str, Enum):
    """Which side of the diff a finding refers to (GitHub review terminology)."""

    left = "LEFT"  # the pre-change ("base") version
    right = "RIGHT"  # the post-change ("head") version — the usual case


class Hunk(BaseModel):
    """A single @@ ... @@ hunk within a file diff."""

    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    header: str
    lines: list[str] = Field(default_factory=list)  # raw lines incl. +/-/space


class FileDiff(BaseModel):
    """All changes to one file."""

    old_path: str | None
    new_path: str | None
    is_new: bool = False
    is_deleted: bool = False
    is_rename: bool = False
    is_binary: bool = False
    hunks: list[Hunk] = Field(default_factory=list)

    @property
    def path(self) -> str:
        """The most relevant path to show the user (new path when present)."""
        return self.new_path or self.old_path or "<unknown>"

    def added_line_numbers(self) -> set[int]:
        """Line numbers (in the new file) that this diff adds or modifies."""
        result: set[int] = set()
        for hunk in self.hunks:
            line_no = hunk.new_start
            for raw in hunk.lines:
                if raw.startswith("+"):
                    result.add(line_no)
                    line_no += 1
                elif raw.startswith("-"):
                    continue
                else:  # context line
                    line_no += 1
        return result


class Finding(BaseModel):
    """One review comment produced by the model."""

    path: str
    line: int = Field(description="1-based line number in the changed file")
    side: Side = Side.right
    severity: Severity = Severity.warning
    category: str = Field(default="general", description="bug, security, style, perf, ...")
    message: str
    suggestion: str | None = None


class ReviewRequest(BaseModel):
    """Everything the engine needs to review a change."""

    diff: str
    # path -> full file content (Phase-1 context). May be partial/empty.
    file_contents: dict[str, str] = Field(default_factory=dict)
    # Optional metadata for nicer prompts / logging.
    title: str | None = None
    description: str | None = None


class ReviewResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    summary: str | None = None
    model: str | None = None
    # Set when the engine declined to review (e.g. diff too large).
    skipped_reason: str | None = None

    @property
    def has_errors(self) -> bool:
        return any(f.severity == Severity.error for f in self.findings)
