import json

from janett.config import Settings
from janett.core.models import ReviewRequest
from janett.core.orchestrator import review

DIFF = """\
diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
 print("hi")
+x = 1 / 0
"""


class StubLLM:
    model = "stub"

    def __init__(self, reply: str):
        self._reply = reply
        self.calls = []

    async def chat(self, messages, *, schema=None, temperature=0.1):
        self.calls.append({"messages": messages, "schema": schema})
        return self._reply


async def test_review_returns_findings():
    reply = json.dumps(
        {"summary": "s", "findings": [{"path": "a.py", "line": 2, "message": "div0", "severity": "error"}]}
    )
    llm = StubLLM(reply)
    result = await review(ReviewRequest(diff=DIFF), llm, Settings())
    assert len(result.findings) == 1
    assert result.model == "stub"
    assert result.has_errors
    # schema is passed through for structured output
    assert llm.calls[0]["schema"] is not None


async def test_empty_diff_skips_llm():
    llm = StubLLM("{}")
    result = await review(ReviewRequest(diff=""), llm, Settings())
    assert result.findings == []
    assert llm.calls == []  # LLM never called


async def test_oversized_diff_skipped():
    llm = StubLLM("{}")
    settings = Settings(max_diff_bytes=10)
    result = await review(ReviewRequest(diff=DIFF), llm, settings)
    assert result.skipped_reason == "diff too large"
    assert llm.calls == []
