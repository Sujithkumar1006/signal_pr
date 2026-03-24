import logging
from dataclasses import dataclass

from fastapi import HTTPException, status

from pr_assistant.ai_input_builder import AIReviewInput, build_ai_review_input
from pr_assistant.ai_review_generation import AIReviewGenerationError, AIReviewOutput, generate_ai_review
from pr_assistant.classifier import FileClassification, classify_changed_files
from pr_assistant.config import get_settings
from pr_assistant.github_app import GitHubAppAuthenticator
from pr_assistant.github_client import (
    GitHubAPIError,
    GitHubClient,
    IssueComment,
    PullRequestData,
)
from pr_assistant.github_webhooks import PullRequestEventContext
from pr_assistant.review_formatter import GitHubReviewComment, format_github_review_comment
from pr_assistant.risk_scoring import RiskAssessment, assess_risk
from pr_assistant.signals import Signal, generate_signals

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReviewPipelineResult:
    pr_data: PullRequestData
    classifications: dict[str, FileClassification]
    signals: list[Signal]
    risk_assessment: RiskAssessment
    review_input: AIReviewInput
    ai_review: AIReviewOutput
    review_comment: GitHubReviewComment
    posted_comment: IssueComment


@dataclass(frozen=True)
class ReviewAnalysis:
    classifications: dict[str, FileClassification]
    signals: list[Signal]
    risk_assessment: RiskAssessment
    review_input: AIReviewInput


def run_review_pipeline(event_context: PullRequestEventContext) -> ReviewPipelineResult:
    authenticator = build_github_app_authenticator()
    client = None
    try:
        client = build_github_client_for_event(authenticator, event_context)
        pr_data = fetch_pr_data(client, event_context)
        analysis = analyze_pull_request(pr_data)
        ai_review = generate_review_output(analysis.review_input)
        review_comment = build_review_comment(ai_review, analysis.risk_assessment)
        posted_comment = post_review_comment(client, event_context, review_comment)

        log_review_run(
            pr_data=pr_data,
            classifications=analysis.classifications,
            signals=analysis.signals,
            risk_assessment=analysis.risk_assessment,
            review_input=analysis.review_input,
            ai_review=ai_review,
            posted_comment=posted_comment,
        )

        return ReviewPipelineResult(
            pr_data=pr_data,
            classifications=analysis.classifications,
            signals=analysis.signals,
            risk_assessment=analysis.risk_assessment,
            review_input=analysis.review_input,
            ai_review=ai_review,
            review_comment=review_comment,
            posted_comment=posted_comment,
        )
    except GitHubAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API error: {exc.message}",
        ) from exc
    except AIReviewGenerationError as exc:
        logger.exception("AI review generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI review generation failed: {exc}",
        ) from exc
    finally:
        if client is not None:
            client.close()
        authenticator.close()


def build_github_app_authenticator() -> GitHubAppAuthenticator:
    settings = get_settings()
    if settings.github_app_id <= 0 or not settings.github_private_key_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GITHUB_APP_ID and GITHUB_PRIVATE_KEY_PATH are required to fetch pull request data",
        )

    return GitHubAppAuthenticator(
        app_id=settings.github_app_id,
        private_key_path=settings.github_private_key_path,
    )


def build_github_client_for_event(
    authenticator: GitHubAppAuthenticator,
    event_context: PullRequestEventContext,
) -> GitHubClient:
    installation_token = authenticator.fetch_installation_token(
        installation_id=event_context.installation_id,
    )
    return GitHubClient(token=installation_token)


def fetch_pr_data(client: GitHubClient, event_context: PullRequestEventContext) -> PullRequestData:
    return client.fetch_pull_request_data(
        repository_full_name=event_context.repository_full_name,
        pull_request_number=event_context.pull_request_number,
    )


def analyze_pull_request(pr_data: PullRequestData) -> ReviewAnalysis:
    classifications = classify_changed_files(pr_data.changed_files)
    signals = generate_signals(pr_data, classifications)
    risk_assessment = assess_risk(signals)
    review_input = build_ai_review_input(
        pr_data,
        classifications=classifications,
        signals=signals,
        risk_assessment=risk_assessment,
    )
    return ReviewAnalysis(
        classifications=classifications,
        signals=signals,
        risk_assessment=risk_assessment,
        review_input=review_input,
    )


def generate_review_output(review_input: AIReviewInput) -> AIReviewOutput:
    return generate_ai_review(review_input)


def build_review_comment(
    ai_review: AIReviewOutput,
    risk_assessment: RiskAssessment,
) -> GitHubReviewComment:
    review_comment = format_github_review_comment(ai_review, risk_assessment)
    logger.info("Built GitHub review comment body=%s", review_comment.body)
    return review_comment


def post_review_comment(
    client: GitHubClient,
    event_context: PullRequestEventContext,
    review_comment: GitHubReviewComment,
) -> IssueComment:
    logger.info(
        "Posting GitHub review comment for %s#%s body_length=%s",
        event_context.repository_full_name,
        event_context.pull_request_number,
        len(review_comment.body),
    )
    posted_comment = client.post_issue_comment(
        repository_full_name=event_context.repository_full_name,
        issue_number=event_context.pull_request_number,
        body=review_comment.body,
    )
    logger.info("Posted comment response=%s", posted_comment)
    return posted_comment


def log_review_run(
    *,
    pr_data: PullRequestData,
    classifications: dict[str, FileClassification],
    signals: list[Signal],
    risk_assessment: RiskAssessment,
    review_input: AIReviewInput,
    ai_review: AIReviewOutput,
    posted_comment: IssueComment,
) -> None:
    logger.info(
        "Fetched pull request data for %s#%s",
        pr_data.pull_request.repository_full_name,
        pr_data.pull_request.number,
    )
    for path, classification in classifications.items():
        logger.info(
            "Classification example: %s -> %s (%s)",
            path,
            classification.category,
            classification.confidence,
        )
    for signal in signals:
        if signal.value:
            logger.info(
                "Active signal: %s severity=%s evidence=%s",
                signal.name,
                signal.severity,
                signal.evidence,
            )
    logger.info(
        "Risk assessment: score=%s label=%s contributing_signals=%s",
        risk_assessment.score,
        risk_assessment.label,
        [
            f"{contribution.name}:{contribution.weight}"
            for contribution in risk_assessment.contributing_signals
        ],
    )
    logger.info(
        "AI review input: files=%s omitted_files=%s diff_chunks=%s omitted_diff_chunks=%s",
        len(review_input.files),
        review_input.omitted_file_count,
        len(review_input.diff_chunks),
        review_input.omitted_diff_chunk_count,
    )
    logger.info("AI review summary: %s", ai_review.summary)
    logger.info("AI review risk explanation: %s", ai_review.risk_explanation)
    logger.info("AI review findings: %s", ai_review.findings)
    logger.info("AI review test gaps: %s", ai_review.test_gaps)
    logger.info("AI review confidence notes: %s", ai_review.confidence_notes)
    logger.info(
        "Posted GitHub review comment: id=%s url=%s",
        posted_comment.id,
        posted_comment.html_url,
    )
