from dataclasses import dataclass

from pr_assistant.classifier import FileClassification, classify_changed_files
from pr_assistant.github_client import PullRequestData


@dataclass(frozen=True)
class Signal:
    name: str
    value: bool | int
    severity: str
    evidence: list[str]


LARGE_DIFF_THRESHOLD = 500
HIGH_CHURN_THRESHOLD = 200
MULTI_LAYER_THRESHOLD = 2
CORE_LAYERS = {"models", "controllers", "services", "policies"}
SENSITIVE_CONFIG_CATEGORIES = {"config", "initializers", "routes", "gem_dependencies", "database_schema"}


def generate_signals(
    pr_data: PullRequestData,
    classifications: dict[str, FileClassification] | None = None,
) -> list[Signal]:
    file_classifications = classifications or classify_changed_files(pr_data.changed_files)
    category_to_paths = build_category_index(file_classifications)
    total_changes = pr_data.pull_request.additions + pr_data.pull_request.deletions
    docs_only = bool(pr_data.changed_files) and all(
        file_classifications[changed_file.path].category == "documentation"
        for changed_file in pr_data.changed_files
    )

    signals = [
        Signal(
            name="files_changed_count",
            value=pr_data.pull_request.changed_file_count,
            severity="low",
            evidence=[str(pr_data.pull_request.changed_file_count)],
        ),
        Signal(
            name="additions_count",
            value=pr_data.pull_request.additions,
            severity="low",
            evidence=[str(pr_data.pull_request.additions)],
        ),
        Signal(
            name="deletions_count",
            value=pr_data.pull_request.deletions,
            severity="low",
            evidence=[str(pr_data.pull_request.deletions)],
        ),
        Signal(
            name="large_diff",
            value=total_changes >= LARGE_DIFF_THRESHOLD,
            severity="high",
            evidence=[str(total_changes)] if total_changes >= LARGE_DIFF_THRESHOLD else [],
        ),
        Signal(
            name="high_churn_file",
            value=has_high_churn_file(pr_data),
            severity="medium",
            evidence=high_churn_paths(pr_data),
        ),
        boolean_category_signal("migration_present", "high", category_to_paths, "migrations"),
        boolean_category_signal("schema_changed", "high", category_to_paths, "database_schema"),
        boolean_category_signal("routes_changed", "high", category_to_paths, "routes"),
        boolean_category_signal("initializer_changed", "high", category_to_paths, "initializers"),
        boolean_category_signal("gemfile_changed", "high", category_to_paths, "gem_dependencies"),
        boolean_category_signal("model_changed", "medium", category_to_paths, "models"),
        boolean_category_signal("controller_changed", "medium", category_to_paths, "controllers"),
        boolean_category_signal("service_changed", "medium", category_to_paths, "services"),
        boolean_category_signal("policy_changed", "medium", category_to_paths, "policies"),
        boolean_category_signal("test_files_changed", "low", category_to_paths, "tests"),
        Signal(
            name="no_tests_changed",
            value="tests" not in category_to_paths and not docs_only,
            severity="medium",
            evidence=non_test_paths(file_classifications) if "tests" not in category_to_paths and not docs_only else [],
        ),
        boolean_category_signal("ci_config_changed", "medium", category_to_paths, "ci_automation"),
        Signal(
            name="sensitive_config_changed",
            value=has_sensitive_config_change(category_to_paths),
            severity="high",
            evidence=sensitive_config_evidence(category_to_paths),
        ),
        Signal(
            name="multiple_core_layers_touched",
            value=count_core_layers(category_to_paths) >= MULTI_LAYER_THRESHOLD,
            severity="high",
            evidence=core_layer_evidence(category_to_paths),
        ),
        Signal(
            name="docs_only_change",
            value=docs_only,
            severity="low",
            evidence=sorted(category_to_paths.get("documentation", [])) if docs_only else [],
        ),
    ]
    return signals


def build_category_index(classifications: dict[str, FileClassification]) -> dict[str, list[str]]:
    category_to_paths: dict[str, list[str]] = {}
    for path, classification in classifications.items():
        category_to_paths.setdefault(classification.category, []).append(path)
    return category_to_paths


def boolean_category_signal(
    name: str,
    severity: str,
    category_to_paths: dict[str, list[str]],
    category: str,
) -> Signal:
    evidence = sorted(category_to_paths.get(category, []))
    return Signal(
        name=name,
        value=bool(evidence),
        severity=severity,
        evidence=evidence,
    )


def has_high_churn_file(pr_data: PullRequestData) -> bool:
    return bool(high_churn_paths(pr_data))


def high_churn_paths(pr_data: PullRequestData) -> list[str]:
    return sorted(
        changed_file.path
        for changed_file in pr_data.changed_files
        if changed_file.additions + changed_file.deletions >= HIGH_CHURN_THRESHOLD
    )


def non_test_paths(classifications: dict[str, FileClassification]) -> list[str]:
    return sorted(
        path
        for path, classification in classifications.items()
        if classification.category != "tests"
    )


def has_sensitive_config_change(category_to_paths: dict[str, list[str]]) -> bool:
    return any(category in category_to_paths for category in SENSITIVE_CONFIG_CATEGORIES)


def sensitive_config_evidence(category_to_paths: dict[str, list[str]]) -> list[str]:
    evidence: list[str] = []
    for category in sorted(SENSITIVE_CONFIG_CATEGORIES):
        evidence.extend(sorted(category_to_paths.get(category, [])))
    return evidence


def count_core_layers(category_to_paths: dict[str, list[str]]) -> int:
    return sum(1 for category in CORE_LAYERS if category in category_to_paths)


def core_layer_evidence(category_to_paths: dict[str, list[str]]) -> list[str]:
    evidence: list[str] = []
    for category in sorted(CORE_LAYERS):
        evidence.extend(sorted(category_to_paths.get(category, [])))
    return evidence
