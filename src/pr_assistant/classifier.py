import re
from dataclasses import dataclass

from pr_assistant.classification_rules import CLASSIFICATION_RULES, ClassificationRule
from pr_assistant.github_client import ChangedFile


@dataclass(frozen=True)
class FileClassification:
    category: str
    confidence: str
    rationale: str


def classify_file_path(path: str) -> FileClassification:
    for rule in CLASSIFICATION_RULES:
        if path_matches_rule(path, rule):
            return FileClassification(
                category=rule.category,
                confidence=rule.confidence,
                rationale=rule.rationale,
            )

    return FileClassification(
        category="other_rails_adjacent",
        confidence="low",
        rationale="Path does not match a narrower Rails-first category",
    )


def classify_changed_file(changed_file: ChangedFile) -> FileClassification:
    return classify_file_path(changed_file.path)


def classify_changed_files(changed_files: list[ChangedFile]) -> dict[str, FileClassification]:
    return {changed_file.path: classify_changed_file(changed_file) for changed_file in changed_files}


def path_matches_rule(path: str, rule: ClassificationRule) -> bool:
    if path in rule.exact:
        return True
    if any(path.startswith(prefix) for prefix in rule.prefixes):
        return True
    if rule.regex and re.match(rule.regex, path):
        return True
    return False
