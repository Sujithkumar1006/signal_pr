from pathlib import Path

from pydantic import ValidationError

from pr_assistant.config import DEFAULT_ENV_FILE, Settings


def test_development_defaults_to_local_webhook_secret():
    settings = Settings(_env_file=None, groq_api_key="secret-key")

    assert settings.github_webhook_secret == "dev-secret"


def test_production_requires_explicit_webhook_secret():
    try:
        Settings(_env_file=None, app_env="production", github_webhook_secret="")
    except ValidationError as exc:
        errors = exc.errors()
    else:
        raise AssertionError("expected production settings validation to fail")

    assert any("GITHUB_WEBHOOK_SECRET is required" in str(error["ctx"]["error"]) for error in errors)


def test_default_env_file_path_is_absolute_and_points_to_project_root():
    assert DEFAULT_ENV_FILE.is_absolute()
    assert DEFAULT_ENV_FILE == Path(__file__).resolve().parents[1] / ".env"


def test_settings_can_load_webhook_secret_from_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GITHUB_WEBHOOK_SECRET=test-secret\nGROQ_API_KEY=test-groq-key\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.github_webhook_secret == "test-secret"


def test_groq_defaults_are_applied_for_ai_setup():
    settings = Settings(_env_file=None, groq_api_key="secret-key")

    assert settings.ai_provider == "groq"
    assert settings.ai_model == "openai/gpt-oss-120b"
    assert settings.groq_base_url == "https://api.groq.com/openai/v1"


def test_groq_requires_api_key():
    try:
        Settings(_env_file=None, ai_provider="groq", groq_api_key="")
    except ValidationError as exc:
        errors = exc.errors()
    else:
        raise AssertionError("expected groq settings validation to fail")

    assert any("GROQ_API_KEY is required" in str(error["ctx"]["error"]) for error in errors)


def test_groq_defaults_model_when_api_key_present():
    settings = Settings(_env_file=None, ai_provider="groq", groq_api_key="secret-key")

    assert settings.ai_model == "openai/gpt-oss-120b"
    assert settings.groq_base_url == "https://api.groq.com/openai/v1"
