from dataclasses import asdict, dataclass

from pr_assistant.classifier import FileClassification, classify_changed_files
from pr_assistant.github_client import ChangedFile, PullRequest, PullRequestData
from pr_assistant.risk_scoring import RiskAssessment, assess_risk
from pr_assistant.signals import Signal, generate_signals

PROMPT_VERSION = "v1"
MAX_DIFF_CHUNKS = 8
MAX_FILE_SUMMARIES = 25
MAX_PATCH_CHARS = 1600

CATEGORY_DIFF_PRIORITIES = {
    "routes": 100,
    "migrations": 95,
    "initializers": 90,
    "gem_dependencies": 90,
    "database_schema": 85,
    "config": 70,
    "services": 65,
    "models": 60,
    "controllers": 60,
    "policies": 55,
    "jobs": 50,
    "mailers": 50,
    "serializers_presenters": 45,
    "components": 40,
    "views": 35,
    "helpers": 30,
    "frontend_assets": 25,
    "tests": 20,
    "ci_automation": 15,
    "documentation": 10,
    "other_rails_adjacent": 5,
}


@dataclass(frozen=True)
class AIFileContext:
    path: str
    status: str
    category: str
    confidence: str
    additions: int
    deletions: int
    patch_available: bool


@dataclass(frozen=True)
class DiffChunk:
    path: str
    category: str
    selection_reason: str
    additions: int
    deletions: int
    patch: str
    patch_truncated: bool


@dataclass(frozen=True)
class AIReviewInput:
    prompt_version: str
    pull_request: PullRequest
    files: list[AIFileContext]
    active_signals: list[Signal]
    risk_assessment: RiskAssessment
    diff_chunks: list[DiffChunk]
    omitted_file_count: int
    omitted_diff_chunk_count: int

    def to_prompt_payload(self) -> dict:
        return {
            "prompt_version": self.prompt_version,
            "pull_request": asdict(self.pull_request),
            "files": [asdict(file_context) for file_context in self.files],
            "active_signals": [
                {
                    "name": signal.name,
                    "value": signal.value,
                    "severity": signal.severity,
                    "evidence": signal.evidence,
                }
                for signal in self.active_signals
            ],
            "risk_assessment": {
                "score": self.risk_assessment.score,
                "label": self.risk_assessment.label,
                "contributing_signals": [
                    asdict(contribution)
                    for contribution in self.risk_assessment.contributing_signals
                ],
            },
            "diff_chunks": [asdict(diff_chunk) for diff_chunk in self.diff_chunks],
            "omitted_file_count": self.omitted_file_count,
            "omitted_diff_chunk_count": self.omitted_diff_chunk_count,
        }


def build_ai_review_input(
    pr_data: PullRequestData,
    classifications: dict[str, FileClassification] | None = None,
    signals: list[Signal] | None = None,
    risk_assessment: RiskAssessment | None = None,
) -> AIReviewInput:
    file_classifications = classifications or classify_changed_files(pr_data.changed_files)
    all_signals = signals or generate_signals(pr_data, file_classifications)
    assessment = risk_assessment or assess_risk(all_signals)
    active_signals = [signal for signal in all_signals if signal.value]

    file_contexts = build_file_contexts(pr_data.changed_files, file_classifications)
    diff_chunks = select_diff_chunks(pr_data.changed_files, file_classifications, active_signals)

    return AIReviewInput(
        prompt_version=PROMPT_VERSION,
        pull_request=pr_data.pull_request,
        files=file_contexts[:MAX_FILE_SUMMARIES],
        active_signals=active_signals,
        risk_assessment=assessment,
        diff_chunks=diff_chunks,
        omitted_file_count=max(len(file_contexts) - MAX_FILE_SUMMARIES, 0),
        omitted_diff_chunk_count=max(count_patch_files(pr_data.changed_files) - len(diff_chunks), 0),
    )


def build_file_contexts(
    changed_files: list[ChangedFile],
    classifications: dict[str, FileClassification],
) -> list[AIFileContext]:
    return [
        AIFileContext(
            path=changed_file.path,
            status=changed_file.status,
            category=classifications[changed_file.path].category,
            confidence=classifications[changed_file.path].confidence,
            additions=changed_file.additions,
            deletions=changed_file.deletions,
            patch_available=changed_file.patch_available,
        )
        for changed_file in changed_files
    ]


def select_diff_chunks(
    changed_files: list[ChangedFile],
    classifications: dict[str, FileClassification],
    active_signals: list[Signal],
) -> list[DiffChunk]:
    signal_path_map = build_signal_path_map(active_signals)
    ranked_files = sorted(
        (
            changed_file
            for changed_file in changed_files
            if changed_file.patch_available and changed_file.patch
        ),
        key=lambda changed_file: (
            file_priority_score(changed_file, classifications[changed_file.path], signal_path_map),
            changed_file.path,
        ),
        reverse=True,
    )

    return [
        build_diff_chunk(
            changed_file,
            classifications[changed_file.path],
            signal_path_map,
        )
        for changed_file in ranked_files[:MAX_DIFF_CHUNKS]
    ]


def build_signal_path_map(active_signals: list[Signal]) -> dict[str, list[str]]:
    signal_path_map: dict[str, list[str]] = {}
    for signal in active_signals:
        for evidence in signal.evidence:
            if "/" in evidence or evidence.endswith(".rb") or evidence.startswith("README"):
                signal_path_map.setdefault(evidence, []).append(signal.name)
    return signal_path_map


def file_priority_score(
    changed_file: ChangedFile,
    classification: FileClassification,
    signal_path_map: dict[str, list[str]],
) -> int:
    score = CATEGORY_DIFF_PRIORITIES.get(classification.category, 0)
    score += min(changed_file.additions + changed_file.deletions, 300) // 25
    if changed_file.path in signal_path_map:
        score += 25
    return score


def build_diff_chunk(
    changed_file: ChangedFile,
    classification: FileClassification,
    signal_path_map: dict[str, list[str]],
) -> DiffChunk:
    return DiffChunk(
        path=changed_file.path,
        category=classification.category,
        selection_reason=selection_reason(
            changed_file.path,
            classification.category,
            signal_path_map,
        ),
        additions=changed_file.additions,
        deletions=changed_file.deletions,
        patch=truncate_patch(changed_file.patch or ""),
        patch_truncated=is_patch_truncated(changed_file.patch or ""),
    )


def selection_reason(path: str, category: str, signal_path_map: dict[str, list[str]]) -> str:
    signals = sorted(signal_path_map.get(path, []))
    if signals:
        return f"Selected for active signals: {', '.join(signals)}"
    return f"Selected for category priority: {category}"


def truncate_patch(patch: str) -> str:
    if len(patch) <= MAX_PATCH_CHARS:
        return patch
    return patch[:MAX_PATCH_CHARS].rstrip() + "\n... [truncated]"


def is_patch_truncated(patch: str) -> bool:
    return len(patch) > MAX_PATCH_CHARS


def count_patch_files(changed_files: list[ChangedFile]) -> int:
    return sum(1 for changed_file in changed_files if changed_file.patch_available and changed_file.patch)
