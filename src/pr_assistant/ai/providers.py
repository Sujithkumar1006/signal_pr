from dataclasses import dataclass

from pr_assistant.config import Settings


@dataclass(frozen=True)
class AIRequest:
    method: str
    url: str
    headers: dict[str, str]
    json: dict
    timeout_seconds: float


class GroqAIProvider:
    def __init__(self, settings: Settings):
        self._settings = settings

    def build_chat_request(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict | None = None,
    ) -> AIRequest:
        payload = {
            "model": self._settings.ai_model,
            "messages": messages,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        return AIRequest(
            method="POST",
            url=f"{self._settings.groq_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout_seconds=self._settings.ai_timeout_seconds,
        )


def build_ai_provider(settings: Settings) -> GroqAIProvider:
    return GroqAIProvider(settings)
