from pr_assistant.ai_input_builder import MAX_DIFF_CHUNKS, MAX_PATCH_CHARS, build_ai_review_input
from pr_assistant.classifier import classify_changed_files
from pr_assistant.github_client import ChangedFile, PullRequest, PullRequestData
from pr_assistant.risk_scoring import assess_risk
from pr_assistant.signals import generate_signals


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


def test_build_ai_review_input_includes_metadata_signals_risk_and_chunks():
    pr_data = make_pr_data(
        [
            ChangedFile("README.md", "modified", 4, 1, True, "@@ -1 +1 @@\n-doc\n+docs"),
            ChangedFile("config/routes.rb", "modified", 5, 1, True, "@@ -1 +1 @@\n-resources :old\n+resources :reviews"),
            ChangedFile(
                "db/migrate/20260321_add_reviews.rb",
                "added",
                20,
                0,
                True,
                "@@ -0,0 +1,20 @@\n+class AddReviews < ActiveRecord::Migration[8.0]\n+end",
            ),
        ],
        additions=29,
        deletions=2,
    )

    classifications = classify_changed_files(pr_data.changed_files)
    signals = generate_signals(pr_data, classifications)
    risk_assessment = assess_risk(signals)

    review_input = build_ai_review_input(pr_data, classifications, signals, risk_assessment)
    payload = review_input.to_prompt_payload()

    assert review_input.prompt_version == "v1"
    assert payload["pull_request"]["title"] == "Add review flow"
    assert payload["risk_assessment"]["label"] == "MEDIUM"
    assert any(signal["name"] == "routes_changed" for signal in payload["active_signals"])
    assert any(signal["name"] == "migration_present" for signal in payload["active_signals"])
    assert [chunk["path"] for chunk in payload["diff_chunks"][:2]] == [
        "config/routes.rb",
        "db/migrate/20260321_add_reviews.rb",
    ]


def test_build_ai_review_input_truncates_large_patches_and_limits_chunk_count():
    large_patch = "@@ -1 +1 @@\n" + ("+a\n" * (MAX_PATCH_CHARS + 200))
    changed_files = [
        ChangedFile(
            f"app/services/service_{index}.rb",
            "modified",
            500 if index == 0 else 80 + index,
            10,
            True,
            large_patch if index == 0 else f"@@ -1 +1 @@\n+service_{index}",
        )
        for index in range(MAX_DIFF_CHUNKS + 3)
    ]
    pr_data = make_pr_data(
        changed_files,
        additions=sum(changed_file.additions for changed_file in changed_files),
        deletions=sum(changed_file.deletions for changed_file in changed_files),
    )

    review_input = build_ai_review_input(pr_data)

    assert len(review_input.diff_chunks) == MAX_DIFF_CHUNKS
    assert review_input.omitted_diff_chunk_count == 3
    truncated_chunks = [diff_chunk for diff_chunk in review_input.diff_chunks if diff_chunk.patch_truncated]
    assert len(truncated_chunks) == 1
    assert truncated_chunks[0].patch.endswith("... [truncated]")


def test_build_ai_review_input_is_deterministic():
    pr_data = make_pr_data(
        [
            ChangedFile("app/models/user.rb", "modified", 12, 3, True, "@@ -1 +1 @@\n+validates :email"),
            ChangedFile("spec/models/user_spec.rb", "modified", 8, 2, True, "@@ -1 +1 @@\n+it 'validates email'"),
        ],
        additions=20,
        deletions=5,
    )

    first = build_ai_review_input(pr_data).to_prompt_payload()
    second = build_ai_review_input(pr_data).to_prompt_payload()

    assert first == second
