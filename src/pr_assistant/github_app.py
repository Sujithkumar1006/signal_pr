from pathlib import Path
from time import time

import httpx
import jwt

from pr_assistant.github_client import DEFAULT_GITHUB_API_BASE_URL, DEFAULT_GITHUB_API_VERSION, GitHubAPIError


class GitHubAppAuthenticator:
    def __init__(
        self,
        *,
        app_id: int,
        private_key_path: str,
        base_url: str = DEFAULT_GITHUB_API_BASE_URL,
        api_version: str = DEFAULT_GITHUB_API_VERSION,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self._app_id = app_id
        self._private_key_path = private_key_path
        self._private_key = Path(private_key_path).read_text(encoding="utf-8")
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": api_version,
            },
        )

    def close(self) -> None:
        self._client.close()

    def build_app_jwt(self) -> str:
        now = int(time())
        return jwt.encode(
            {
                "iat": now - 60,
                "exp": now + 600,
                "iss": str(self._app_id),
            },
            self._private_key,
            algorithm="RS256",
        )

    def fetch_installation_token(self, *, installation_id: int) -> str:
        response = self._client.post(
            f"/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {self.build_app_jwt()}",
            },
        )
        if not response.is_success:
            message = response.text.strip() or "GitHub App authentication failed"
            raise GitHubAPIError(status_code=response.status_code, message=message)

        payload = response.json()
        if not isinstance(payload, dict):
            raise GitHubAPIError(status_code=response.status_code, message="GitHub App auth response was not a JSON object")

        token = payload.get("token")
        if not isinstance(token, str) or not token:
            raise GitHubAPIError(status_code=response.status_code, message="GitHub App auth response did not contain a token")

        return token
