# Setting up the GitHub bot

Janett's GitHub bot is a **GitHub App** that listens for pull-request events and
posts inline review comments.

## 1. Create the App

Go to **Settings → Developer settings → GitHub Apps → New GitHub App** (personal
or org), then:

- **Webhook URL**: `https://<your-deploy>/webhook/github`
  (for local testing, use a smee.io / ngrok URL — see below).
- **Webhook secret**: generate a long random string. You'll set this as
  `GITHUB_WEBHOOK_SECRET`.
- **Permissions** (Repository):
  - **Pull requests**: Read & write  (to post reviews/comments)
  - **Contents**: Read-only  (to fetch file context)
  - **Metadata**: Read-only  (implicit)
- **Subscribe to events**: **Pull request**.

Create the App, then on its page:

- Note the **App ID** → `GITHUB_APP_ID`.
- **Generate a private key** (downloads a `.pem`) → `GITHUB_PRIVATE_KEY`.

## 2. Configure Janett

```bash
GITHUB_APP_ID=123456
GITHUB_WEBHOOK_SECRET=the-secret-you-set
# Single-line env var: encode newlines as \n
GITHUB_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----
```

To turn a `.pem` file into a single-line value:

```bash
awk 'BEGIN{ORS="\\n"} {print}' your-key.pem
```

## 3. Install the App

On the App page → **Install App** → choose the account → select the repositories
you want Janett to review.

## 4. Test it

Open a pull request (or push a new commit to an existing one). Janett will:

1. Receive the `pull_request` webhook (`opened` / `synchronize` / `reopened` /
   `ready_for_review`).
2. Verify the HMAC signature, ack `200`, and review in the background.
3. Post a single review with a summary and inline comments on changed lines.

Draft PRs are skipped until marked ready.

## Local webhook testing

You don't need to deploy to test. Forward GitHub webhooks to your machine:

```bash
# Option A: smee.io
npx smee-client --url https://smee.io/<your-channel> --target http://localhost:8000/webhook/github

# Option B: ngrok
ngrok http 8000   # then set the App webhook URL to the ngrok https URL
```

Run the server locally and open a PR against an installed repo:

```bash
uv run uvicorn janett.api.app:app --reload
```

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `/webhook/github` → `503` | `GITHUB_*` env vars not set. Check `/health`. |
| `/webhook/github` → `401` | Signature mismatch — `GITHUB_WEBHOOK_SECRET` differs from the App's secret. |
| No comments posted | Check server logs (`janett.github` logger). Common causes: comment lines outside the diff (filtered), permissions missing, or the diff exceeded a guardrail. |
| 422 from GitHub on review | The commit SHA or line/side didn't match the diff — usually a stale head SHA; re-trigger with a new push. |
