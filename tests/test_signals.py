from pr_assistant.classifier import classify_changed_files
from pr_assistant.github_client import ChangedFile, PullRequest, PullRequestData
from pr_assistant.signals import generate_signals


def make_pr_data(changed_files: list[ChangedFile], *, additions: int, deletions: int) -> PullRequestData:
    return PullRequestData(
        pull_request=PullRequest(
            repository_full_name="acme/widgets",
            number=42,
            title="Test PR",
            body="",
            author="sujith",
            base_branch="main",
            head_branch="feature/test",
            changed_file_count=len(changed_files),
            additions=additions,
            deletions=deletions,
        ),
        changed_files=changed_files,
        diff_text="diff --git a/file b/file",
    )


def signal_map(pr_data: PullRequestData) -> dict[str, object]:
    classifications = classify_changed_files(pr_data.changed_files)
    return {signal.name: signal for signal in generate_signals(pr_data, classifications)}


def test_generates_expected_category_and_test_signals():
    pr_data = make_pr_data(
        [
            ChangedFile("app/models/user.rb", "modified", 20, 5, True, "@@"),
            ChangedFile("config/routes.rb", "modified", 5, 1, True, "@@"),
            ChangedFile("db/migrate/20260321_add_reviews.rb", "added", 30, 0, True, "@@"),
        ],
        additions=55,
        deletions=6,
    )

    signals = signal_map(pr_data)

    assert signals["model_changed"].value is True
    assert signals["routes_changed"].value is True
    assert signals["migration_present"].value is True
    assert signals["test_files_changed"].value is False
    assert signals["no_tests_changed"].value is True


def test_generates_large_diff_high_churn_and_multi_layer_signals():
    pr_data = make_pr_data(
        [
            ChangedFile("app/models/user.rb", "modified", 140, 80, True, "@@"),
            ChangedFile("app/controllers/users_controller.rb", "modified", 90, 50, True, "@@"),
            ChangedFile("app/services/review_runner.rb", "modified", 80, 70, True, "@@"),
            ChangedFile("spec/services/review_runner_spec.rb", "modified", 10, 5, True, "@@"),
        ],
        additions=320,
        deletions=205,
    )

    signals = signal_map(pr_data)

    assert signals["large_diff"].value is True
    assert signals["high_churn_file"].value is True
    assert signals["multiple_core_layers_touched"].value is True
    assert signals["test_files_changed"].value is True
    assert signals["no_tests_changed"].value is False


def test_recognizes_docs_only_changes():
    pr_data = make_pr_data(
        [
            ChangedFile("README.md", "modified", 10, 3, True, "@@"),
            ChangedFile("docs/architecture.md", "modified", 12, 4, True, "@@"),
        ],
        additions=22,
        deletions=7,
    )

    signals = signal_map(pr_data)

    assert signals["docs_only_change"].value is True
    assert signals["no_tests_changed"].value is False
    assert signals["migration_present"].value is False


def test_recognizes_sensitive_config_changes():
    pr_data = make_pr_data(
        [
            ChangedFile("config/initializers/feature_flags.rb", "modified", 7, 2, True, "@@"),
            ChangedFile("Gemfile.lock", "modified", 20, 10, True, "@@"),
        ],
        additions=27,
        deletions=12,
    )

    signals = signal_map(pr_data)

    assert signals["initializer_changed"].value is True
    assert signals["gemfile_changed"].value is True
    assert signals["sensitive_config_changed"].value is True
    assert "config/initializers/feature_flags.rb" in signals["sensitive_config_changed"].evidence
