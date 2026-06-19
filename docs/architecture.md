# Architecture

Janett is built around one principle: **a transport-agnostic review engine** that
knows nothing about HTTP, git, or GitHub. Every front-end is thin plumbing that
turns its world into a `ReviewRequest` and renders the `ReviewResult` back.

```
                         ┌──────────────── Review Core (src/janett/core) ────────────────┐
                         │  ReviewRequest ─► review() ─► ReviewResult(Finding[])          │
                         │                                                                │
                         │  parse_diff ─► build_messages ─► LLMClient.chat ─► parse_      │
                         │  (diff.py)     (prompt.py)        (llm/*)          review_      │
                         │                                                   output       │
                         │                                                   (findings.py) │
                         └───────▲───────────────────────────────────────────▲────────────┘
                                 │                                             │
              ┌──────────────────┴───────┐                  ┌──────────────────┴───────────┐
              │ Local CLI                │                  │ FastAPI server (api/)         │
              │ cli/main.py              │                  │  POST /review   (sync)        │
              │  └ vcs/local.py          │                  │  POST /webhook/github         │
              │     git diff → request   │                  │   └ verify HMAC, ack 200      │
              │  └ cli/render.py         │                  │   └ BackgroundTask:           │
              │     findings → terminal  │                  │       tasks.process_pull_     │
              └──────────────────────────┘                  │       request → vcs/github.py │
                                                            └───────────────────────────────┘

  LLMClient (llm/base.py)  ──  OllamaClient (default)  |  OpenAICompatClient (prod/remote)
```

## The data path

1. **A diff comes in** — from `git diff` locally, or fetched from the GitHub PR API.
2. **`parse_diff`** (`core/diff.py`) turns the unified diff into `FileDiff`/`Hunk`
   objects and computes, per file, the set of line numbers the change *added or
   modified*.
3. **Context is gathered** — Phase 1 context is the full content of each changed
   file (capped by `MAX_FILE_BYTES`), so the model sees more than the raw hunk.
4. **`build_messages`** (`core/prompt.py`) builds the system+user chat messages,
   including the explicit JSON output shape.
5. **`LLMClient.chat`** is called with a JSON schema for structured output.
6. **`parse_review_output`** (`core/findings.py`) parses the model's JSON
   (tolerating code fences, bare arrays, and minor field-name drift) and then
   **drops any finding that doesn't point at a changed line**. This is the single
   most important guardrail: it kills hallucinated comments and avoids GitHub
   rejecting comments on lines outside the diff.
7. The `ReviewResult` is rendered: to the terminal (CLI) or as a GitHub review
   with inline comments.

## Key types (`core/models.py`)

| Type | Role |
|------|------|
| `ReviewRequest` | `diff` + `file_contents` (+ optional title/description) |
| `FileDiff` / `Hunk` | parsed diff; `FileDiff.added_line_numbers()` drives the guardrail |
| `Finding` | one comment: `path`, `line`, `side`, `severity`, `category`, `message`, `suggestion` |
| `ReviewResult` | `findings` + `summary` + `model`; `has_errors`, `skipped_reason` |

## Extension points

- **New LLM backend** — implement the `LLMClient` protocol (`llm/base.py`, one
  `chat` method) and wire it into `llm/factory.py`. The core never changes.
- **New VCS / source** — produce a `ReviewRequest` and consume a `ReviewResult`.
  `vcs/local.py` and `vcs/github.py` are the two reference implementations.
- **Guardrails** — `MAX_DIFF_BYTES`, `MAX_FILES`, `MAX_FILE_BYTES` are enforced in
  `core/orchestrator.py` and the GitHub task.

## Why a background task for GitHub

GitHub expects a webhook response within ~10s, but a review (especially on CPU
Ollama) takes much longer. So `routes_github.py` verifies the signature, enqueues
a FastAPI `BackgroundTask`, and returns `200` immediately; `tasks.py` does the
slow work and posts the review afterward. A durable queue (Redis + worker) is a
Phase 2 upgrade — see the roadmap in the README.
