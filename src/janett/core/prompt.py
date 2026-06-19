"""Prompt construction for a review pass."""

from __future__ import annotations

from .models import FileDiff, ReviewRequest

SYSTEM_PROMPT = """\
You are Janett, a meticulous senior software engineer performing a code review.
You are given a unified diff and, for context, the full content of the changed
files. Review ONLY the changes in the diff — do not comment on unrelated code.

Focus, in priority order:
1. Bugs and correctness issues (logic errors, off-by-one, null/None handling,
   race conditions, incorrect error handling).
2. Security problems (injection, secrets, auth/authz, unsafe deserialization).
3. Performance issues that matter.
4. Clear maintainability/readability problems.

Rules:
- Comment only on lines that were added or modified in the diff.
- Be specific and actionable. No praise, no nitpicks about formatting that a
  linter would catch, no speculative "consider maybe" comments.
- If the change is fine, return an empty list of findings.
- `line` must be the 1-based line number in the NEW version of the file.
- Keep each message to 1-3 sentences. Include a concrete `suggestion` when useful.

Respond with a single JSON object of exactly this shape (no prose outside it):
{
  "summary": "one short paragraph summarizing the review",
  "findings": [
    {
      "path": "relative/file/path.py",
      "line": 42,
      "side": "RIGHT",
      "severity": "info | warning | error",
      "category": "bug | security | perf | style | general",
      "message": "what is wrong and why",
      "suggestion": "optional concrete fix"
    }
  ]
}
"""


def _format_file_context(req: ReviewRequest, files: list[FileDiff]) -> str:
    blocks: list[str] = []
    for f in files:
        content = req.file_contents.get(f.path)
        if not content:
            continue
        blocks.append(f"=== FILE: {f.path} ===\n{content}")
    if not blocks:
        return "(no file context available)"
    return "\n\n".join(blocks)


def build_messages(req: ReviewRequest, files: list[FileDiff]) -> list[dict[str, str]]:
    """Build the chat messages for the review request."""
    header = ""
    if req.title:
        header += f"Pull request title: {req.title}\n"
    if req.description:
        header += f"Description: {req.description}\n"

    user = (
        f"{header}\n"
        "## Changed files (full content for context)\n"
        f"{_format_file_context(req, files)}\n\n"
        "## Diff to review\n"
        f"```diff\n{req.diff}\n```\n\n"
        "Return your review as structured findings."
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
