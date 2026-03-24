from pr_assistant.classifier import classify_changed_files
from pr_assistant.github_client import ChangedFile, PullRequest, PullRequestData
from pr_assistant.risk_scoring import assess_risk
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


def build_risk_assessment(pr_data: PullRequestData):
    classifications = classify_changed_files(pr_data.changed_files)
    signals = generate_signals(pr_data, classifications)
    return assess_risk(signals)


def test_docs_only_change_scores_low():
    pr_data = make_pr_data(
        [
            ChangedFile("README.md", "modified", 10, 3, True, "@@"),
            ChangedFile("docs/architecture.md", "modified", 12, 4, True, "@@"),
        ],
        additions=22,
        deletions=7,
    )

    risk_assessment = build_risk_assessment(pr_data)

    assert risk_assessment.score == 0
    assert risk_assessment.label == "LOW"
    assert risk_assessment.contributing_signals[0].name == "docs_only_change"
    assert risk_assessment.contributing_signals[0].weight == -4


def test_routes_and_migration_change_scores_medium():
    pr_data = make_pr_data(
        [
            ChangedFile("app/models/user.rb", "modified", 20, 5, True, "@@"),
            ChangedFile("config/routes.rb", "modified", 5, 1, True, "@@"),
            ChangedFile("db/migrate/20260321_add_reviews.rb", "added", 30, 0, True, "@@"),
        ],
        additions=55,
        deletions=6,
    )

    risk_assessment = build_risk_assessment(pr_data)

    assert risk_assessment.score == 9
    assert risk_assessment.label == "MEDIUM"
    assert [contribution.name for contribution in risk_assessment.contributing_signals[:2]] == [
        "routes_changed",
        "migration_present",
    ]


def test_large_multilayer_change_scores_high():
    pr_data = make_pr_data(
        [
            ChangedFile("app/models/user.rb", "modified", 140, 80, True, "@@"),
            ChangedFile("app/controllers/users_controller.rb", "modified", 90, 50, True, "@@"),
            ChangedFile("app/services/review_runner.rb", "modified", 80, 70, True, "@@"),
            ChangedFile("config/initializers/feature_flags.rb", "modified", 7, 2, True, "@@"),
            ChangedFile("Gemfile.lock", "modified", 20, 10, True, "@@"),
            ChangedFile("spec/services/review_runner_spec.rb", "modified", 10, 5, True, "@@"),
        ],
        additions=347,
        deletions=217,
    )

    risk_assessment = build_risk_assessment(pr_data)

    assert risk_assessment.score == 14
    assert risk_assessment.label == "HIGH"
    assert risk_assessment.contributing_signals[0].name in {"initializer_changed", "gemfile_changed"}
    assert len(risk_assessment.contributing_signals) == 5


def test_test_file_change_slightly_reduces_score():
    pr_data = make_pr_data(
        [
            ChangedFile("app/services/review_runner.rb", "modified", 30, 5, True, "@@"),
            ChangedFile("spec/services/review_runner_spec.rb", "modified", 15, 2, True, "@@"),
        ],
        additions=45,
        deletions=7,
    )

    risk_assessment = build_risk_assessment(pr_data)

    assert risk_assessment.score == 0
    assert risk_assessment.label == "LOW"
    assert [contribution.name for contribution in risk_assessment.contributing_signals] == [
        "service_changed",
        "test_files_changed",
    ]
