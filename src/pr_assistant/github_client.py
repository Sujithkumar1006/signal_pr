from dataclasses import dataclass

import httpx


DEFAULT_GITHUB_API_BASE_URL = "https://api.github.com"
DEFAULT_GITHUB_API_VERSION = "2022-11-28"


@dataclass(frozen=True)
class PullRequest:
    repository_full_name: str
    number: int
    title: str
    body: str
    author: str
    base_branch: str
    head_branch: str
    changed_file_count: int
    additions: int
    deletions: int


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status: str
    additions: int
    deletions: int
    patch_available: bool
    patch: str | None


@dataclass(frozen=True)
class PullRequestData:
    pull_request: PullRequest
    changed_files: list[ChangedFile]
    diff_text: str


class GitHubAPIError(RuntimeError):
    def __init__(self, *, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class GitHubClient:
    def __init__(
        self,
        *,
        token: str,
        base_url: str = DEFAULT_GITHUB_API_BASE_URL,
        api_version: str = DEFAULT_GITHUB_API_VERSION,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": api_version,
            },
        )

    def close(self) -> None:
        self._client.close()

    def fetch_pull_request(self, *, repository_full_name: str, pull_request_number: int) -> PullRequest:
        payload = self._get_json(f"/repos/{repository_full_name}/pulls/{pull_request_number}")
        return PullRequest(
            repository_full_name=repository_full_name,
            number=require_int(payload, "number"),
            title=require_str(payload, "title"),
            body=optional_str(payload.get("body")),
            author=require_nested_str(payload, "user", "login"),
            base_branch=require_nested_str(payload, "base", "ref"),
            head_branch=require_nested_str(payload, "head", "ref"),
            changed_file_count=require_int(payload, "changed_files"),
            additions=require_int(payload, "additions"),
            deletions=require_int(payload, "deletions"),
        )

    def fetch_changed_files(
        self,
        *,
        repository_full_name: str,
        pull_request_number: int,
    ) -> list[ChangedFile]:
        files: list[ChangedFile] = []
        next_path = f"/repos/{repository_full_name}/pulls/{pull_request_number}/files?per_page=100"

        while next_path:
            response = self._get_response(next_path)
            payload = self._decode_json(response)
            if not isinstance(payload, list):
                raise GitHubAPIError(
                    status_code=response.status_code,
                    message="GitHub files response was not a JSON array",
                )

            for item in payload:
                if not isinstance(item, dict):
                    raise GitHubAPIError(
                        status_code=response.status_code,
                        message="GitHub files response contained a non-object entry",
                    )

                patch = item.get("patch")
                files.append(
                    ChangedFile(
                        path=require_str(item, "filename"),
                        status=require_str(item, "status"),
                        additions=require_int(item, "additions"),
                        deletions=require_int(item, "deletions"),
                        patch_available=isinstance(patch, str),
                        patch=patch if isinstance(patch, str) else None,
                    )
                )

            next_link = response.links.get("next")
            next_path = next_link["url"] if next_link else ""

        return files

    def fetch_pull_request_diff(self, *, repository_full_name: str, pull_request_number: int) -> str:
        response = self._get_response(
            f"/repos/{repository_full_name}/pulls/{pull_request_number}",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        return response.text

    def fetch_pull_request_data(
        self,
        *,
        repository_full_name: str,
        pull_request_number: int,
    ) -> PullRequestData:
        pull_request = self.fetch_pull_request(
            repository_full_name=repository_full_name,
            pull_request_number=pull_request_number,
        )
        changed_files = self.fetch_changed_files(
            repository_full_name=repository_full_name,
            pull_request_number=pull_request_number,
        )
        diff_text = self.fetch_pull_request_diff(
            repository_full_name=repository_full_name,
            pull_request_number=pull_request_number,
        )
        return PullRequestData(
            pull_request=pull_request,
            changed_files=changed_files,
            diff_text=diff_text,
        )

    def _get_json(self, path: str) -> dict:
        response = self._get_response(path)
        payload = self._decode_json(response)
        if not isinstance(payload, dict):
            raise GitHubAPIError(
                status_code=response.status_code,
                message="GitHub response was not a JSON object",
            )
        return payload

    def _decode_json(self, response: httpx.Response) -> dict | list:
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubAPIError(
                status_code=response.status_code,
                message="GitHub response was not valid JSON",
            ) from exc

    def _get_response(self, path: str, headers: dict[str, str] | None = None) -> httpx.Response:
        response = self._client.get(path, headers=headers)
        if response.is_success:
            return response

        message = response.text.strip() or "GitHub API request failed"
        raise GitHubAPIError(status_code=response.status_code, message=message)


def require_str(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise GitHubAPIError(status_code=200, message=f"Missing or invalid field: {key}")
    return value


def optional_str(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise GitHubAPIError(status_code=200, message="Invalid field type: body")
    return value


def require_int(payload: dict, key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise GitHubAPIError(status_code=200, message=f"Missing or invalid field: {key}")
    return value


def require_nested_str(payload: dict, *keys: str) -> str:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            raise GitHubAPIError(status_code=200, message=f"Missing field: {'.'.join(keys)}")
        current = current[key]

    if not isinstance(current, str) or not current:
        raise GitHubAPIError(status_code=200, message=f"Missing or invalid field: {'.'.join(keys)}")
    return current
