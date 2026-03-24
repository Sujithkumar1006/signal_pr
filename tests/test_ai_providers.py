from pr_assistant.ai import GroqAIProvider, build_ai_provider
from pr_assistant.config import Settings


def test_build_ai_provider_returns_groq_provider():
    provider = build_ai_provider(Settings(_env_file=None, groq_api_key="secret-key"))

    assert isinstance(provider, GroqAIProvider)


def test_groq_provider_builds_openai_compatible_request():
    settings = Settings(
        ai_provider="groq",
        groq_api_key="secret-key",
        ai_model="openai/gpt-oss-120b",
        ai_timeout_seconds=12.5,
    )
    provider = GroqAIProvider(settings)

    request = provider.build_chat_request(
        messages=[{"role": "user", "content": "Review this PR"}],
        response_format={"type": "json_object"},
    )

    assert request.method == "POST"
    assert request.url == "https://api.groq.com/openai/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer secret-key"
    assert request.json["model"] == "openai/gpt-oss-120b"
    assert request.json["messages"] == [{"role": "user", "content": "Review this PR"}]
    assert request.json["response_format"] == {"type": "json_object"}
    assert request.timeout_seconds == 12.5
