from pathlib import Path

import httpx

from pr_assistant.github_app import GitHubAppAuthenticator


def test_build_app_jwt_delegates_to_pyjwt(monkeypatch, tmp_path):
    private_key_path = tmp_path / "signalpr.pem"
    private_key_path.write_text("private-key", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_encode(payload, private_key, algorithm):
        captured["payload"] = payload
        captured["private_key"] = private_key
        captured["algorithm"] = algorithm
        return "signed.jwt.token"

    monkeypatch.setattr("pr_assistant.github_app.jwt.encode", fake_encode)

    authenticator = GitHubAppAuthenticator(
        app_id=12345,
        private_key_path=str(private_key_path),
    )

    token = authenticator.build_app_jwt()

    assert token == "signed.jwt.token"
    assert captured["private_key"] == "private-key"
    assert captured["algorithm"] == "RS256"
    assert captured["payload"]["iss"] == "12345"


def test_fetch_installation_token_returns_token_from_github(tmp_path, monkeypatch):
    private_key_path = tmp_path / "signalpr.pem"
    private_key_path.write_text("private-key", encoding="utf-8")
    monkeypatch.setattr(
        "pr_assistant.github_app.jwt.encode",
        lambda payload, private_key, algorithm: "signed.jwt.token",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer signed.jwt.token"
        assert request.url.path == "/app/installations/98765/access_tokens"
        return httpx.Response(201, json={"token": "installation-token"})

    authenticator = GitHubAppAuthenticator(
        app_id=12345,
        private_key_path=str(private_key_path),
        transport=httpx.MockTransport(handler),
    )

    token = authenticator.fetch_installation_token(installation_id=98765)

    assert token == "installation-token"
