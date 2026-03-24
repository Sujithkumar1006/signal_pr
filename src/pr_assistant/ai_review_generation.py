import json
from dataclasses import dataclass

import httpx

from pr_assistant.ai.providers import build_ai_provider
from pr_assistant.ai_input_builder import AIReviewInput
from pr_assistant.config import Settings, get_settings

SYSTEM_PROMPT = """You are PR Assistant, an AI-first pull request reviewer for Rails repositories.
Return only valid JSON with these keys:
- summary: string
- risk_explanation: string
- findings: array of short strings, maximum 5 items
- test_gaps: array of short strings, maximum 5 items
- confidence_notes: array of short strings, maximum 3 items

Rules:
- Ground every statement in the provided PR context, signals, risk assessment, or diff chunks.
- Keep findings high-signal and concise.
- Do not mention files or facts that are not present in the input.
- If confidence is limited because context was omitted, say so in confidence_notes.
"""


@dataclass(frozen=True)
class AIReviewOutput:
    summary: str
    risk_explanation: str
    findings: list[str]
    test_gaps: list[str]
    confidence_notes: list[str]


class AIReviewGenerationError(RuntimeError):
    pass


def build_review_messages(review_input: AIReviewInput) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(review_input.to_prompt_payload(), separators=(",", ":"), ensure_ascii=True),
        },
    ]


def generate_ai_review(
    review_input: AIReviewInput,
    *,
    settings: Settings | None = None,
    transport: httpx.BaseTransport | None = None,
) -> AIReviewOutput:
    resolved_settings = settings or get_settings()
    provider = build_ai_provider(resolved_settings)
    request = provider.build_chat_request(
        messages=build_review_messages(review_input),
        response_format={"type": "json_object"},
    )

    with httpx.Client(timeout=request.timeout_seconds, transport=transport) as client:
        response = client.request(
            method=request.method,
            url=request.url,
            headers=request.headers,
            json=request.json,
        )

    if not response.is_success:
        raise AIReviewGenerationError(response.text.strip() or "AI provider request failed")

    payload = decode_json_response(response)
    content = extract_message_content(payload)
    review_json = parse_review_json(content)
    return validate_review_output(review_json)


def decode_json_response(response: httpx.Response) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AIReviewGenerationError("AI provider response was not valid JSON") from exc

    if not isinstance(payload, dict):
        raise AIReviewGenerationError("AI provider response was not a JSON object")
    return payload


def extract_message_content(payload: dict) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIReviewGenerationError("AI provider response did not include choices")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise AIReviewGenerationError("AI provider choice was not an object")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise AIReviewGenerationError("AI provider response did not include a message")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise AIReviewGenerationError("AI provider response content was empty")
    return content


def parse_review_json(content: str) -> dict:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIReviewGenerationError("AI review content was not valid JSON") from exc

    if not isinstance(payload, dict):
        raise AIReviewGenerationError("AI review content was not a JSON object")
    return payload


def validate_review_output(payload: dict) -> AIReviewOutput:
    summary = require_non_empty_string(payload, "summary")
    risk_explanation = require_non_empty_string(payload, "risk_explanation")
    findings = require_string_list(payload, "findings", max_items=5)
    test_gaps = require_string_list(payload, "test_gaps", max_items=5)
    confidence_notes = require_string_list(payload, "confidence_notes", max_items=3)

    return AIReviewOutput(
        summary=summary,
        risk_explanation=risk_explanation,
        findings=findings,
        test_gaps=test_gaps,
        confidence_notes=confidence_notes,
    )


def require_non_empty_string(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AIReviewGenerationError(f"AI review field {key} was missing or empty")
    return value.strip()


def require_string_list(payload: dict, key: str, *, max_items: int) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise AIReviewGenerationError(f"AI review field {key} was not a list")
    if len(value) > max_items:
        raise AIReviewGenerationError(f"AI review field {key} exceeded {max_items} items")

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise AIReviewGenerationError(f"AI review field {key} contained an invalid item")
        normalized.append(item.strip())
    return normalized
