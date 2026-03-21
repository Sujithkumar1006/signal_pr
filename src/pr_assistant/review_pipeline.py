import logging

from fastapi import HTTPException, status

from pr_assistant.classifier import classify_changed_files
from pr_assistant.config import get_settings
from pr_assistant.github_app import GitHubAppAuthenticator
from pr_assistant.github_client import GitHubAPIError, GitHubClient, PullRequestData
from pr_assistant.github_webhooks import PullRequestEventContext
from pr_assistant.signals import generate_signals

logger = logging.getLogger(__name__)


def fetch_pr_data_for_event(event_context: PullRequestEventContext) -> PullRequestData:
    settings = get_settings()
    if settings.github_app_id <= 0 or not settings.github_private_key_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GITHUB_APP_ID and GITHUB_PRIVATE_KEY_PATH are required to fetch pull request data",
        )

    authenticator = GitHubAppAuthenticator(
        app_id=settings.github_app_id,
        private_key_path=settings.github_private_key_path,
    )
    try:
        installation_token = authenticator.fetch_installation_token(
            installation_id=event_context.installation_id,
        )
        client = GitHubClient(token=installation_token)
        try:
            return client.fetch_pull_request_data(
                repository_full_name=event_context.repository_full_name,
                pull_request_number=event_context.pull_request_number,
            )
        finally:
            client.close()
    except GitHubAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API error: {exc.message}",
        ) from exc
    finally:
        authenticator.close()


def log_classification_examples(pr_data: PullRequestData) -> None:
    classifications = classify_changed_files(pr_data.changed_files)
    signals = generate_signals(pr_data, classifications)
    logger.info(
        "Fetched pull request data for %s#%s",
        pr_data.pull_request.repository_full_name,
        pr_data.pull_request.number,
    )
    # logger.info(
    #     "Changed files count: %s, diff length: %s",
    #     len(pr_data.changed_files),
    #     len(pr_data.diff_text),
    # )
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
