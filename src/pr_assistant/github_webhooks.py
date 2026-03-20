import hashlib
import hmac
import json
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from pr_assistant.config import get_settings

SUPPORTED_PULL_REQUEST_ACTIONS = {"opened", "reopened", "synchronize"}


@dataclass(frozen=True)
class PullRequestEventContext:
    action: str
    repository_full_name: str
    repository_owner: str
    repository_name: str
    pull_request_number: int
    pull_request_title: str
    pull_request_author: str
    base_branch: str
    head_branch: str


async def parse_pull_request_webhook(request: Request) -> tuple[str, PullRequestEventContext | None]:
    event_name = request.headers.get("X-GitHub-Event")
    print(f'========================================')
    print(f'Event name is #{event_name}')
    print(f'========================================')
    if event_name != "pull_request":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported GitHub event",
        )

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    verify_github_signature(body=body, signature=signature)

    payload = load_json_payload(body)
    action = payload.get("action")
    if action not in SUPPORTED_PULL_REQUEST_ACTIONS:
        return action or "unknown", None

    return action, PullRequestEventContext(
        action=action,
        repository_full_name=require_nested_str(payload, "repository", "full_name"),
        repository_owner=require_nested_str(payload, "repository", "owner", "login"),
        repository_name=require_nested_str(payload, "repository", "name"),
        pull_request_number=require_nested_int(payload, "pull_request", "number"),
        pull_request_title=require_nested_str(payload, "pull_request", "title"),
        pull_request_author=require_nested_str(payload, "pull_request", "user", "login"),
        base_branch=require_nested_str(payload, "pull_request", "base", "ref"),
        head_branch=require_nested_str(payload, "pull_request", "head", "ref"),
    )


def verify_github_signature(*, body: bytes, signature: str | None) -> None:
    settings = get_settings()
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )

    expected_signature = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook signature",
        )


def load_json_payload(body: bytes) -> dict:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload must be a JSON object",
        )

    return payload


def require_nested_str(payload: dict, *keys: str) -> str:
    value = require_nested_value(payload, *keys)
    if not isinstance(value, str) or not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing or invalid field: {'.'.join(keys)}",
        )
    return value


def require_nested_int(payload: dict, *keys: str) -> int:
    value = require_nested_value(payload, *keys)
    if not isinstance(value, int):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing or invalid field: {'.'.join(keys)}",
        )
    return value


def require_nested_value(payload: dict, *keys: str):
    current = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing field: {'.'.join(keys)}",
            )
        current = current[key]
    return current
