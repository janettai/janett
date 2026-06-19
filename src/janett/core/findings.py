"""Parse and validate the LLM's structured output into Findings.

The model is asked to return a JSON object shaped like ``ReviewOutput`` below.
We tolerate common deviations (markdown code fences, a bare array, slightly
wrong field names) and then drop any finding that doesn't point at a line the
diff actually touched.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from .models import FileDiff, Finding, ReviewResult, Severity, Side


class ReviewOutput(BaseModel):
    """The JSON shape we ask the model to produce (used as the output schema)."""

    summary: str = ""
    findings: list[Finding] = []


def output_json_schema() -> dict:
    """JSON schema passed to the LLM for structured/constrained decoding."""
    return ReviewOutput.model_json_schema()


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _load_json(text: str):
    """Parse JSON from model output, tolerating fences and surrounding prose."""
    text = text.strip()
    # 1. Try the whole thing (handles a bare object or a bare array).
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 2. Try a fenced ```json ... ``` block.
    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # 3. Fall back to the first {...} or [...] block.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def parse_review_output(raw: str, files: list[FileDiff]) -> ReviewResult:
    """Turn raw model text into a validated :class:`ReviewResult`."""
    data = _load_json(raw)
    if data is None:
        return ReviewResult(
            findings=[],
            summary="(could not parse model output)",
        )

    # Accept either {"findings": [...]} or a bare [...] of findings.
    if isinstance(data, list):
        data = {"findings": data}

    try:
        output = ReviewOutput.model_validate(data)
    except ValidationError:
        output = _salvage(data)

    valid = _filter_to_diff(output.findings, files)
    return ReviewResult(findings=valid, summary=output.summary or None)


def _salvage(data: dict) -> ReviewOutput:
    """Best-effort parse when strict validation fails."""
    findings: list[Finding] = []
    for item in data.get("findings", []) or []:
        if not isinstance(item, dict):
            continue
        try:
            findings.append(
                Finding(
                    path=str(item.get("path") or item.get("file") or ""),
                    line=int(item.get("line") or item.get("line_number") or 0),
                    side=_coerce_side(item.get("side")),
                    severity=_coerce_severity(item.get("severity")),
                    category=str(item.get("category") or "general"),
                    message=str(item.get("message") or item.get("comment") or ""),
                    suggestion=item.get("suggestion"),
                )
            )
        except (ValueError, TypeError):
            continue
    return ReviewOutput(summary=str(data.get("summary") or ""), findings=findings)


def _coerce_severity(value: object) -> Severity:
    try:
        return Severity(str(value).lower())
    except ValueError:
        return Severity.warning


def _coerce_side(value: object) -> Side:
    try:
        return Side(str(value).upper())
    except ValueError:
        return Side.right


def _filter_to_diff(findings: list[Finding], files: list[FileDiff]) -> list[Finding]:
    """Keep only findings that reference a line actually changed by the diff.

    This is the key guardrail against the model hallucinating comments on
    unchanged code (and GitHub rejects comments on lines outside the diff).
    """
    added_by_path: dict[str, set[int]] = {
        f.path: f.added_line_numbers() for f in files
    }
    kept: list[Finding] = []
    for f in findings:
        if not f.message.strip():
            continue
        added = added_by_path.get(f.path)
        if added is None:
            # Try a basename match — models sometimes drop directory prefixes.
            matches = [p for p in added_by_path if p.endswith("/" + f.path) or p.endswith(f.path)]
            if len(matches) == 1:
                f.path = matches[0]
                added = added_by_path[matches[0]]
        if added and f.line in added:
            kept.append(f)
    return kept
