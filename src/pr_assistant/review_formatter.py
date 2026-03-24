from dataclasses import dataclass

from pr_assistant.ai_review_generation import AIReviewOutput
from pr_assistant.risk_scoring import RiskAssessment

MAX_FINDINGS = 5
MAX_TEST_GAPS = 5


@dataclass(frozen=True)
class GitHubReviewComment:
    body: str


def format_github_review_comment(
    ai_review: AIReviewOutput,
    risk_assessment: RiskAssessment,
) -> GitHubReviewComment:
    lines = [
        "## PR Assistant Review",
        "",
        f"**Risk:** `{risk_assessment.label}` ({risk_assessment.score})",
        "",
        f"**Summary**  ",
        ai_review.summary,
        "",
        f"**Why It Matters**  ",
        ai_review.risk_explanation,
    ]

    if ai_review.findings:
        lines.extend(
            [
                "",
                "**Key Findings**",
                *[f"- {finding}" for finding in ai_review.findings[:MAX_FINDINGS]],
            ]
        )

    if ai_review.test_gaps:
        lines.extend(
            [
                "",
                "**Test Gaps**",
                *[f"- {test_gap}" for test_gap in ai_review.test_gaps[:MAX_TEST_GAPS]],
            ]
        )

    if ai_review.confidence_notes:
        lines.extend(
            [
                "",
                "**Confidence Notes**",
                *[f"- {note}" for note in ai_review.confidence_notes],
            ]
        )

    return GitHubReviewComment(body="\n".join(lines).strip())
