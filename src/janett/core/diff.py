"""A small, dependency-free unified-diff parser.

Handles the `git diff` / GitHub PR diff format: `diff --git` headers, rename
and new/deleted-file markers, binary markers, and `@@` hunks.
"""

from __future__ import annotations

import re

from .models import FileDiff, Hunk

_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_lines>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_lines>\d+))? @@(?P<rest>.*)$"
)


def _strip_prefix(path: str) -> str:
    """Drop the leading a/ or b/ that git puts on diff paths."""
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def parse_diff(diff_text: str) -> list[FileDiff]:
    """Parse a unified diff into a list of :class:`FileDiff`."""
    files: list[FileDiff] = []
    current: FileDiff | None = None
    current_hunk: Hunk | None = None

    def flush_hunk() -> None:
        nonlocal current_hunk
        if current is not None and current_hunk is not None:
            current.hunks.append(current_hunk)
        current_hunk = None

    def flush_file() -> None:
        nonlocal current
        flush_hunk()
        if current is not None:
            files.append(current)
        current = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            flush_file()
            # `diff --git a/foo b/foo`
            parts = line.split(" ")
            old = _strip_prefix(parts[2]) if len(parts) > 2 else None
            new = _strip_prefix(parts[3]) if len(parts) > 3 else None
            current = FileDiff(old_path=old, new_path=new)
            continue

        if current is None:
            continue

        if line.startswith("new file mode"):
            current.is_new = True
        elif line.startswith("deleted file mode"):
            current.is_deleted = True
        elif line.startswith("rename from "):
            current.is_rename = True
            current.old_path = _strip_prefix(line[len("rename from ") :])
        elif line.startswith("rename to "):
            current.is_rename = True
            current.new_path = _strip_prefix(line[len("rename to ") :])
        elif line.startswith("Binary files") or line.startswith("GIT binary patch"):
            current.is_binary = True
        elif current_hunk is None and line.startswith("--- "):
            path = line[4:].strip()
            current.old_path = None if path == "/dev/null" else _strip_prefix(path)
        elif current_hunk is None and line.startswith("+++ "):
            path = line[4:].strip()
            current.new_path = None if path == "/dev/null" else _strip_prefix(path)
        elif line.startswith("@@"):
            flush_hunk()
            m = _HUNK_RE.match(line)
            if not m:
                continue
            current_hunk = Hunk(
                old_start=int(m.group("old_start")),
                old_lines=int(m.group("old_lines") or 1),
                new_start=int(m.group("new_start")),
                new_lines=int(m.group("new_lines") or 1),
                header=m.group("rest").strip(),
            )
        elif current_hunk is not None and line and line[0] in "+- \\":
            # Body line of a hunk (\\ marks "No newline at end of file").
            current_hunk.lines.append(line)

    flush_file()
    return files


def changed_paths(files: list[FileDiff]) -> list[str]:
    """Paths worth fetching content for (skip deleted & binary files)."""
    return [
        f.path
        for f in files
        if not f.is_deleted and not f.is_binary and f.new_path is not None
    ]
