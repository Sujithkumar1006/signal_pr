from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from pr_assistant.config import get_settings, validate_settings
from pr_assistant.github_webhooks import parse_pull_request_webhook
from starlette.middleware.trustedhost import TrustedHostMiddleware



@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_settings()
    yield


app = FastAPI(
    title="PR Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.trycloudflare.com",]
)

@app.get("/health")
async def healthcheck() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@app.post("/webhooks/github")
async def github_webhook(request: Request) -> dict:
    action, event_context = await parse_pull_request_webhook(request)

    if event_context is None:
        return {
            "status": "ignored",
            "event": "pull_request",
            "action": action,
            "reason": "unsupported pull_request action",
        }

    return {
        "status": "accepted",
        "event": "pull_request",
        "action": event_context.action,
        "repository": event_context.repository_full_name,
        "pull_request_number": event_context.pull_request_number,
        "pull_request_title": event_context.pull_request_title,
        "pull_request_author": event_context.pull_request_author,
        "base_branch": event_context.base_branch,
        "head_branch": event_context.head_branch,
    }
