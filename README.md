# PR Assistant

PR Assistant is an AI-first pull request review system built as a GitHub App. It receives `pull_request` webhooks, fetches PR data from GitHub, derives deterministic review signals, and uses AI to generate a concise review summary.

The MVP is intentionally Rails-first. Deterministic logic provides structured context. AI is responsible for the final human-facing review output.

## Current Status

Implemented:
- FastAPI app boot and health check
- Environment-based settings with startup validation
- GitHub webhook signature verification for `pull_request` events
- Pull request webhook payload parsing for supported actions
- Groq AI provider setup and live API validation
- GitHub client for PR metadata, changed files, and diff fetching

Not implemented yet:
- Real GitHub token-based fetch wired into the webhook flow
- Rails file classification
- Signal generation
- Risk scoring
- AI review input builder
- AI review generation from PR context
- GitHub PR comment posting

## Architecture

1. GitHub sends a `pull_request` webhook to the FastAPI service.
2. The webhook layer validates the signature and extracts core PR context.
3. The GitHub client fetches PR metadata, changed files, and unified diff content.
4. Rails-first classification and deterministic signals prepare structured review context.
5. Risk scoring produces explicit, explainable risk inputs.
6. The AI layer generates summary, findings, and test guidance.
7. The service posts one concise review comment back to GitHub.

## Local Setup

Requirements:
- Python 3.13+
- A virtualenv at `.venv`
- A valid Groq API key

Install dependencies:

```bash
.venv/bin/pip install -e .
```

Create your local env file:

```bash
cp .env.example .env
```

Update `.env` with your actual values:

```env
APP_NAME=PR Assistant
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=info
GITHUB_WEBHOOK_SECRET=your-webhook-secret
AI_PROVIDER=groq
AI_MODEL=openai/gpt-oss-120b
AI_TIMEOUT_SECONDS=30
GROQ_API_KEY=your-real-groq-api-key
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

## Running The Server

From the project root:

```bash
PYTHONPATH=src .venv/bin/uvicorn pr_assistant.main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Tests

Run the current test suite:

```bash
PYTHONPATH=src .venv/bin/pytest
```

Targeted suites:

```bash
PYTHONPATH=src .venv/bin/pytest tests/test_config.py
PYTHONPATH=src .venv/bin/pytest tests/test_ai_providers.py
PYTHONPATH=src .venv/bin/pytest tests/test_github_client.py
```

## WIP

Near-term work:
- Wire GitHub authentication into runtime config
- Connect webhook intake to the GitHub client
- Add Rails-first file classification
- Add deterministic signal generation
- Add deterministic risk scoring
- Build the AI review input payload
- Generate AI review output from fetched PR context
- Format and post a single GitHub PR comment

Cleanup items:
- Remove debug `print` statements from startup and webhook handling
- Add a proper logger
- Add integration tests for webhook-to-fetch flow
- Add end-to-end tests with mocked GitHub and Groq responses

## Notes

- `.env` is ignored by git. Keep secrets there.
- `.env.example` is the committed template.
- Groq is the current AI provider for both development and production paths.
