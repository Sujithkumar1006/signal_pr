from dataclasses import dataclass
from typing import Literal

from pr_assistant.signals import Signal


LOW_RISK_MAX_SCORE = 3
MEDIUM_RISK_MAX_SCORE = 9
MAX_CONTRIBUTING_SIGNALS = 5

SIGNAL_WEIGHTS = {
    "migration_present": 3,
    "schema_changed": 2,
    "routes_changed": 3,
    "initializer_changed": 3,
    "gemfile_changed": 3,
    "sensitive_config_changed": 1,
    "multiple_core_layers_touched": 2,
    "large_diff": 2,
    "high_churn_file": 1,
    "policy_changed": 1,
    "ci_config_changed": 1,
    "no_tests_changed": 1,
    "model_changed": 1,
    "controller_changed": 1,
    "service_changed": 1,
    "docs_only_change": -4,
    "test_files_changed": -1,
}


@dataclass(frozen=True)
class RiskContribution:
    name: str
    weight: int
    evidence: list[str]


@dataclass(frozen=True)
class RiskAssessment:
    score: int
    label: Literal["LOW", "MEDIUM", "HIGH"]
    contributing_signals: list[RiskContribution]


def assess_risk(signals: list[Signal]) -> RiskAssessment:
    contributions: list[RiskContribution] = []
    score = 0

    for signal in signals:
        weight = signal_weight(signal)
        if weight == 0:
            continue
        score += weight
        contributions.append(
            RiskContribution(
                name=signal.name,
                weight=weight,
                evidence=signal.evidence,
            )
        )

    bounded_score = max(score, 0)
    return RiskAssessment(
        score=bounded_score,
        label=risk_label_for_score(bounded_score),
        contributing_signals=top_contributing_signals(contributions),
    )


def signal_weight(signal: Signal) -> int:
    if not isinstance(signal.value, bool) or not signal.value:
        return 0
    return SIGNAL_WEIGHTS.get(signal.name, 0)


def risk_label_for_score(score: int) -> Literal["LOW", "MEDIUM", "HIGH"]:
    if score <= LOW_RISK_MAX_SCORE:
        return "LOW"
    if score <= MEDIUM_RISK_MAX_SCORE:
        return "MEDIUM"
    return "HIGH"


def top_contributing_signals(contributions: list[RiskContribution]) -> list[RiskContribution]:
    return sorted(
        contributions,
        key=lambda contribution: (abs(contribution.weight), contribution.weight, contribution.name),
        reverse=True,
    )[:MAX_CONTRIBUTING_SIGNALS]
