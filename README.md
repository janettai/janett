# Janett

[![CI](https://github.com/janettai/janett/actions/workflows/ci.yml/badge.svg)](https://github.com/janettai/janett/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A Greptile-like AI code review bot. One transport-agnostic review engine, two
front-ends:

- **Local CLI bot** — review your `git diff` in the terminal.
- **GitHub bot** — a GitHub App that reviews pull requests and posts inline comments.

Uses **Ollama by default** (local, free). The LLM backend is pluggable, so in
production you point it at a remote OpenAI-compatible endpoint.

## Architecture

```
Review Core (diff → context → prompt → LLM → findings)
  ├── Local CLI  (git diff → core → terminal)
  └── FastAPI    (POST /review,  POST /webhook/github → core → PR comments)

LLM client interface:  OllamaClient (default)  |  OpenAICompatClient (prod/remote)
```

The core (`src/janett/core`) knows nothing about HTTP or GitHub. It takes a diff
plus file contents and returns structured `Finding`s. Everything else is plumbing.

See [`docs/architecture.md`](docs/architecture.md) for the full data-flow and
extension points.

## Documentation

| Doc | What's in it |
|-----|--------------|
| [docs/architecture.md](docs/architecture.md) | Engine design, data path, key types, how to add an LLM or VCS backend |
| [docs/configuration.md](docs/configuration.md) | Every environment variable, with defaults |
| [docs/github-app.md](docs/github-app.md) | Creating the GitHub App, installing it, local webhook testing, troubleshooting |
| [docs/deployment.md](docs/deployment.md) | Deploying the API to Railway and the production LLM setup |

## Project layout

```
src/janett/
  config.py            # settings (env vars)
  core/                # the transport-agnostic review engine
    models.py          #   ReviewRequest, ReviewResult, Finding, FileDiff, Hunk
    diff.py            #   unified-diff parser
    prompt.py          #   prompt construction
    findings.py        #   parse + validate model output (drops out-of-diff findings)
    orchestrator.py    #   review() — the entry point
  llm/                 # pluggable LLM clients
    base.py            #   LLMClient protocol
    ollama.py          #   default backend
    openai_compat.py   #   prod / remote backend
    factory.py         #   build client from config
  vcs/
    local.py           # git diff → ReviewRequest
    github.py          # GitHub App auth, fetch PR diff, post review
  api/
    app.py             # FastAPI app + /health
    routes_review.py   # POST /review
    routes_github.py   # POST /webhook/github (HMAC verify, ack, enqueue)
    tasks.py           # background PR review
  cli/
    main.py            # `janett review` CLI
    render.py          # terminal output
tests/                 # diff parser, findings parser, orchestrator
```

## Setup

```bash
uv sync --extra dev          # create venv + install
cp .env.example .env         # configure
```

For local use, run Ollama and pull a coder model:

```bash
ollama serve &
ollama pull qwen2.5-coder:7b
```

## Local CLI

```bash
uv run janett review                 # working tree vs HEAD
uv run janett review --staged        # staged changes
uv run janett review --base main     # main..HEAD
uv run janett review --remote https://my-janett.up.railway.app   # use a deployed API
```

Exits non-zero if any `error`-severity findings (handy in CI / pre-commit).

## API server

```bash
uv run uvicorn janett.api.app:app --reload
curl -s localhost:8000/health
curl -s localhost:8000/review -H 'content-type: application/json' \
  -d '{"diff": "<unified diff>", "file_contents": {}}'
```

## GitHub bot

1. Create a **GitHub App**: permissions **Pull requests: Read & write**,
   **Contents: Read**; subscribe to the **Pull request** event.
2. Set the webhook URL to `https://<your-deploy>/webhook/github` and a webhook secret.
3. Put `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY` (PEM, newlines as `\n`), and
   `GITHUB_WEBHOOK_SECRET` in the environment.
4. Install the App on a repo and open a PR.

Locally, forward webhooks with [smee.io](https://smee.io) or ngrok to
`http://localhost:8000/webhook/github`.

## Deploy to Railway

This repo ships a `Dockerfile` and `railway.toml` (single web service,
healthcheck on `/health`).

Since Railway has no GPU, run the LLM elsewhere and set:

```
LLM_PROVIDER=openai
OPENAI_BASE_URL=<remote OpenAI-compatible endpoint, e.g. a hosted provider or remote Ollama /v1>
OPENAI_API_KEY=<key>
OPENAI_MODEL=<model>
```

plus the three `GITHUB_*` secrets. Then point the GitHub App webhook at the
Railway URL.

## Tests

```bash
uv run pytest
```

## Roadmap (Phase 2)

- Whole-repo RAG context (pgvector + embeddings, tree-sitter chunking).
- Redis + worker queue; review persistence; comment dedup across re-pushes.
- `@janett` re-review commands; PR summary; per-repo `.janett.yml` config.

## License

[MIT](LICENSE)
