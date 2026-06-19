# Configuration

All configuration is via environment variables (or a local `.env` file). Defaults
live in `src/janett/config.py`; copy `.env.example` to `.env` to get started.

## LLM backend

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` (local/dev) or `openai` (prod/remote, OpenAI-compatible). |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL. |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Model used when provider is `ollama`. |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint. Point at a hosted provider **or** a remote Ollama box (`http://host:11434/v1`). |
| `OPENAI_API_KEY` | _(empty)_ | Bearer token for the endpoint above. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used when provider is `openai`. |
| `LLM_TEMPERATURE` | `0.1` | Sampling temperature (low = more deterministic reviews). |
| `LLM_TIMEOUT_SECONDS` | `300` | Per-request timeout. CPU Ollama can be slow; keep this generous. |

> **Why two providers?** Ollama is the free, local default. Railway has no GPU, so
> in production set `LLM_PROVIDER=openai` and point `OPENAI_BASE_URL` at something
> GPU-backed. The review engine is identical either way.

## GitHub App (only for the GitHub bot)

| Variable | Description |
|----------|-------------|
| `GITHUB_APP_ID` | Numeric App ID from the App's settings page. |
| `GITHUB_PRIVATE_KEY` | The App's PEM private key. In a single-line env var, encode newlines as `\n` — `config.py` normalizes them back. |
| `GITHUB_WEBHOOK_SECRET` | The webhook secret you set on the App; used to verify `X-Hub-Signature-256`. |

If any of these are unset, `/webhook/github` returns `503` and `/health` reports
`github_configured: false`. The CLI and `/review` work without them.

## Guardrails

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_DIFF_BYTES` | `400000` | Diffs larger than this are skipped (`skipped_reason: "diff too large"`). |
| `MAX_FILES` | `60` | PRs touching more files than this are skipped. |
| `MAX_FILE_BYTES` | `60000` | Per-file context cap; larger files are omitted from context (still reviewed via the diff). |

## Inspecting the live config

```bash
curl -s localhost:8000/health | jq
# { "status": "ok", "llm_provider": "ollama", "model": "qwen2.5-coder:7b", "github_configured": false }
```
