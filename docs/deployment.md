# Deploying to Railway

The repo ships a `Dockerfile` and `railway.toml` configured for a single web
service with a healthcheck on `/health`.

## The GPU caveat

Railway has **no GPU**, so running Ollama there means CPU inference — too slow for
real PR reviews. The recommended setup keeps Ollama as the *local* default and
points production at a GPU-backed, OpenAI-compatible endpoint:

```
LLM_PROVIDER=openai
OPENAI_BASE_URL=<remote endpoint>   # hosted provider, or your own Ollama box at http://host:11434/v1
OPENAI_API_KEY=<key>
OPENAI_MODEL=<model>
```

`OPENAI_BASE_URL` can be:
- a hosted inference provider (OpenAI-compatible), or
- **your own Ollama machine** with a GPU — Ollama exposes an OpenAI-compatible API
  at `<host>:11434/v1`. Janett doesn't care which; it's one env var.

## Steps

1. **Create the service** (from the repo root):

   ```bash
   railway init            # or create a project in the dashboard
   railway up              # builds the Dockerfile and deploys
   ```

   Or connect the GitHub repo in the Railway dashboard for push-to-deploy.

2. **Set environment variables** (dashboard → Variables, or `railway variables`):

   ```
   LLM_PROVIDER=openai
   OPENAI_BASE_URL=...
   OPENAI_API_KEY=...
   OPENAI_MODEL=...
   GITHUB_APP_ID=...
   GITHUB_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----
   GITHUB_WEBHOOK_SECRET=...
   ```

   Railway injects `PORT`; the Dockerfile/`railway.toml` already bind to it.

3. **Verify** once deployed:

   ```bash
   curl -s https://<service>.up.railway.app/health
   ```

4. **Point the GitHub App webhook** at
   `https://<service>.up.railway.app/webhook/github`
   (see [github-app.md](github-app.md)).

## Notes

- The healthcheck path is `/health` (set in `railway.toml`).
- Restart policy: on failure, up to 3 retries.
- No database or Redis is required for the MVP. A durable job queue is a Phase 2
  item (see the README roadmap); until then, reviews run as in-process background
  tasks and are lost if the service restarts mid-review (GitHub will re-deliver on
  the next push).
