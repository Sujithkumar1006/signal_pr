import json

import httpx
import pytest

from pr_assistant.github_client import ChangedFile, GitHubAPIError, GitHubClient, IssueComment, PullRequest


def test_fetch_pull_request_returns_core_metadata():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "number": 42,
                "title": "Add review pipeline",
                "body": "Implements the review flow",
                "user": {"login": "sujith"},
                "base": {"ref": "main"},
                "head": {"ref": "feature/review"},
                "changed_files": 3,
                "additions": 120,
                "deletions": 18,
            },
        )
    )
    client = GitHubClient(token="test-token", transport=transport)

    pull_request = client.fetch_pull_request(
        repository_full_name="acme/widgets",
        pull_request_number=42,
    )

    assert pull_request == PullRequest(
        repository_full_name="acme/widgets",
        number=42,
        title="Add review pipeline",
        body="Implements the review flow",
        author="sujith",
        base_branch="main",
        head_branch="feature/review",
        changed_file_count=3,
        additions=120,
        deletions=18,
    )


def test_fetch_changed_files_returns_all_pages_and_patch_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        if str(request.url).endswith("/files?per_page=100"):
            return httpx.Response(
                200,
                json=[
                    {
                        "filename": "app/models/user.rb",
                        "status": "modified",
                        "additions": 12,
                        "deletions": 2,
                        "patch": "@@ -1 +1 @@",
                    }
                ],
                headers={
                    "Link": '<https://api.github.com/repos/acme/widgets/pulls/42/files?per_page=100&page=2>; rel="next"'
                },
            )

        assert str(request.url).endswith("/files?per_page=100&page=2")
        return httpx.Response(
            200,
            json=[
                {
                    "filename": "db/migrate/20260320_add_reviews.rb",
                    "status": "added",
                    "additions": 24,
                    "deletions": 0,
                }
            ],
        )

    client = GitHubClient(token="test-token", transport=httpx.MockTransport(handler))

    changed_files = client.fetch_changed_files(
        repository_full_name="acme/widgets",
        pull_request_number=42,
    )

    assert changed_files == [
        ChangedFile(
            path="app/models/user.rb",
            status="modified",
            additions=12,
            deletions=2,
            patch_available=True,
            patch="@@ -1 +1 @@",
        ),
        ChangedFile(
            path="db/migrate/20260320_add_reviews.rb",
            status="added",
            additions=24,
            deletions=0,
            patch_available=False,
            patch=None,
        ),
    ]


def test_fetch_pull_request_diff_returns_unified_diff_text():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Accept"] == "application/vnd.github.v3.diff"
        return httpx.Response(200, text="diff --git a/app/models/user.rb b/app/models/user.rb")

    client = GitHubClient(token="test-token", transport=httpx.MockTransport(handler))

    diff_text = client.fetch_pull_request_diff(
        repository_full_name="acme/widgets",
        pull_request_number=42,
    )

    assert diff_text.startswith("diff --git")


def test_fetch_pull_request_data_combines_all_pr_context():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        query = request.url.query.decode()

        if path.endswith("/pulls/42") and not query:
            accept_header = request.headers["Accept"]
            if accept_header == "application/vnd.github+json":
                return httpx.Response(
                    200,
                    json={
                        "number": 42,
                        "title": "Add review pipeline",
                        "body": None,
                        "user": {"login": "sujith"},
                        "base": {"ref": "main"},
                        "head": {"ref": "feature/review"},
                        "changed_files": 1,
                        "additions": 12,
                        "deletions": 2,
                    },
                )

            assert accept_header == "application/vnd.github.v3.diff"
            return httpx.Response(200, text="diff --git a/app/services/review.rb b/app/services/review.rb")

        if path.endswith("/files") and query == "per_page=100":
            return httpx.Response(
                200,
                json=[
                    {
                        "filename": "app/services/review.rb",
                        "status": "modified",
                        "additions": 12,
                        "deletions": 2,
                        "patch": "@@ -1,2 +1,12 @@",
                    }
                ],
            )

        raise AssertionError(f"unexpected request: {request.url}")

    client = GitHubClient(token="test-token", transport=httpx.MockTransport(handler))

    pr_data = client.fetch_pull_request_data(
        repository_full_name="acme/widgets",
        pull_request_number=42,
    )

    assert pr_data.pull_request.title == "Add review pipeline"
    assert pr_data.pull_request.body == ""
    assert len(pr_data.changed_files) == 1
    assert pr_data.diff_text.startswith("diff --git")


def test_github_api_errors_are_surfaced_cleanly():
    client = GitHubClient(
        token="test-token",
        transport=httpx.MockTransport(lambda request: httpx.Response(404, text="Not Found")),
    )

    with pytest.raises(GitHubAPIError) as exc:
        client.fetch_pull_request(repository_full_name="acme/widgets", pull_request_number=404)

    assert exc.value.status_code == 404
    assert exc.value.message == "Not Found"


def test_post_issue_comment_returns_created_comment():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/repos/acme/widgets/issues/42/comments"
        assert request.headers["Authorization"] == "Bearer test-token"
        assert json.loads(request.content.decode()) == {"body": "review body"}
        return httpx.Response(
            201,
            json={
                "id": 987654,
                "body": "review body",
                "html_url": "https://github.com/acme/widgets/pull/42#issuecomment-987654",
            },
        )

    client = GitHubClient(token="test-token", transport=httpx.MockTransport(handler))

    comment = client.post_issue_comment(
        repository_full_name="acme/widgets",
        issue_number=42,
        body="review body",
    )

    assert comment == IssueComment(
        id=987654,
        body="review body",
        html_url="https://github.com/acme/widgets/pull/42#issuecomment-987654",
    )
