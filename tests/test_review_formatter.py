from pr_assistant.ai_review_generation import AIReviewOutput
from pr_assistant.review_formatter import format_github_review_comment
from pr_assistant.risk_scoring import RiskAssessment, RiskContribution


def test_format_github_review_comment_renders_expected_sections():
    ai_review = AIReviewOutput(
        summary="Adds review routes and a migration.",
        risk_explanation="Medium risk because routes changed and data shape is evolving.",
        findings=[
            "Verify the migration is reversible.",
            "Check the new route authorization path.",
        ],
        test_gaps=[
            "Add request coverage for the review endpoint.",
            "Add migration rollback coverage if applicable.",
        ],
        confidence_notes=["Review focused on selected high-risk diff chunks."],
    )
    risk_assessment = RiskAssessment(
        score=9,
        label="MEDIUM",
        contributing_signals=[
            RiskContribution(name="routes_changed", weight=3, evidence=["config/routes.rb"]),
            RiskContribution(name="migration_present", weight=3, evidence=["db/migrate/20260321_add_reviews.rb"]),
        ],
    )

    comment = format_github_review_comment(ai_review, risk_assessment)

    assert "## PR Assistant Review" in comment.body
    assert "**Risk:** `MEDIUM` (9)" in comment.body
    assert "**Summary**" in comment.body
    assert "**Why It Matters**" in comment.body
    assert "**Key Findings**" in comment.body
    assert "**Test Gaps**" in comment.body
    assert "**Confidence Notes**" in comment.body
    assert "- Verify the migration is reversible." in comment.body
