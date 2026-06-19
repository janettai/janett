from janett.core.diff import parse_diff
from janett.core.findings import parse_review_output
from janett.core.models import Severity

DIFF = """\
diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,3 @@
 import os
+x = 1 / 0
+y = 2
"""


def _files():
    return parse_diff(DIFF)


def test_parses_well_formed_object():
    raw = """{
      "summary": "one issue",
      "findings": [
        {"path": "src/app.py", "line": 2, "severity": "error",
         "category": "bug", "message": "division by zero"}
      ]
    }"""
    result = parse_review_output(raw, _files())
    assert len(result.findings) == 1
    assert result.findings[0].severity == Severity.error
    assert result.summary == "one issue"


def test_strips_code_fences():
    raw = '```json\n{"findings": [{"path": "src/app.py", "line": 2, "message": "x"}]}\n```'
    result = parse_review_output(raw, _files())
    assert len(result.findings) == 1


def test_drops_findings_outside_diff():
    # line 1 is a context line (not added) -> dropped.
    raw = '{"findings": [{"path": "src/app.py", "line": 1, "message": "nope"}]}'
    result = parse_review_output(raw, _files())
    assert result.findings == []


def test_bare_array_accepted():
    raw = '[{"path": "src/app.py", "line": 3, "message": "ok"}]'
    result = parse_review_output(raw, _files())
    assert len(result.findings) == 1


def test_basename_match_fixes_path():
    raw = '{"findings": [{"path": "app.py", "line": 2, "message": "fix path"}]}'
    result = parse_review_output(raw, _files())
    assert len(result.findings) == 1
    assert result.findings[0].path == "src/app.py"


def test_unparseable_output_is_safe():
    result = parse_review_output("the model rambled with no json", _files())
    assert result.findings == []
