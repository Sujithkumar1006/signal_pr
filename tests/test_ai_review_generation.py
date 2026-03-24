import json

import httpx
import pytest

from pr_assistant.ai_input_builder import build_ai_review_input
from pr_assistant.ai_review_generation import (
    AIReviewGenerationError,
    build_review_messages,
    generate_ai_review,
)
from pr_assistant.github_client import ChangedFile, PullRequest, PullRequestData
from pr_assistant.config import Settings


def make_pr_data(changed_files: list[ChangedFile], *, additions: int, deletions: int) -> PullRequestData:
    return PullRequestData(
        pull_request=PullRequest(
            repository_full_name="acme/widgets",
            number=42,
            title="Add review flow",
            body="Build review pipeline",
            author="sujith",
            base_branch="main",
            head_branch="feature/review",
            changed_file_count=len(changed_files),
            additions=additions,
            deletions=deletions,
        ),
        changed_files=changed_files,
        diff_text="diff --git a/file b/file",
    )


def make_review_input():
    pr_data = make_pr_data(
        [
            ChangedFile("config/routes.rb", "modified", 5, 1, True, "@@ -1 +1 @@\n+resources :reviews"),
            ChangedFile(
                "db/migrate/20260321_add_reviews.rb",
                "added",
                20,
                0,
                True,
                "@@ -0,0 +1,20 @@\n+class AddReviews < ActiveRecord::Migration[8.0]\n+end",
            ),
        ],
        additions=25,
        deletions=1,
    )
    return build_ai_review_input(pr_data)


def test_build_review_messages_embeds_prompt_payload():
    review_input = make_review_input()

    messages = build_review_messages(review_input)

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    payload = json.loads(messages[1]["content"])
    assert payload["prompt_version"] == "v1"
    assert payload["risk_assessment"]["label"] == "MEDIUM"
    assert payload["pull_request"]["title"] == "Add review flow"


def test_generate_ai_review_returns_validated_output():
    review_input = make_review_input()

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "Adds review routes and migration support.",
                                    "risk_explanation": "Medium risk because routes and a migration changed without tests.",
                                    "findings": [
                                        "Verify the migration is reversible.",
                                        "Confirm the new route does not expose unintended write paths.",
                                    ],
                                    "test_gaps": [
                                        "Add request coverage for the new review route.",
                                        "Add migration safety coverage if applicable.",
                                    ],
                                    "confidence_notes": ["Review focused on selected high-risk diff chunks."],
                                }
                            )
                        }
                    }
                ]
            },
        )

    output = generate_ai_review(
        review_input,
        settings=Settings(_env_file=None, groq_api_key="secret-key"),
        transport=httpx.MockTransport(handler),
    )

    assert output.summary == "Adds review routes and migration support."
    assert len(output.findings) == 2
    assert output.confidence_notes == ["Review focused on selected high-risk diff chunks."]


def test_generate_ai_review_rejects_malformed_output():
    review_input = make_review_input()

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "",
                                    "risk_explanation": "Medium risk.",
                                    "findings": ["One"],
                                    "test_gaps": [],
                                    "confidence_notes": [],
                                }
                            )
                        }
                    }
                ]
            },
        )
    )

    with pytest.raises(AIReviewGenerationError) as exc:
        generate_ai_review(
            review_input,
            settings=Settings(_env_file=None, groq_api_key="secret-key"),
            transport=transport,
        )

    assert "summary" in str(exc.value)


def test_generate_ai_review_rejects_provider_failure():
    review_input = make_review_input()
    transport = httpx.MockTransport(lambda request: httpx.Response(502, text="bad gateway"))

    with pytest.raises(AIReviewGenerationError) as exc:
        generate_ai_review(
            review_input,
            settings=Settings(_env_file=None, groq_api_key="secret-key"),
            transport=transport,
        )

    assert "bad gateway" in str(exc.value)
