import json
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.models.learning import LearningCheckinDraft, LearningSubject


class OpenAICheckinDraftError(RuntimeError):
    pass


class OpenAICheckinDraftAdapter:
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        client_factory: Callable[..., httpx.Client] = httpx.Client,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.model = model or settings.openai_checkin_model
        self.timeout_seconds = timeout_seconds or settings.openai_timeout_seconds
        self.client_factory = client_factory

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def draft_checkin(self, text: str) -> LearningCheckinDraft:
        if not self.api_key:
            raise OpenAICheckinDraftError("OPENAI_API_KEY is not configured")

        try:
            with self.client_factory(timeout=self.timeout_seconds) as client:
                response = client.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=self._build_request(text),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenAICheckinDraftError(f"OpenAI check-in draft request failed: {exc}") from exc

        try:
            payload = self._extract_json(response.json())
            return LearningCheckinDraft(
                **payload,
                original_text=text,
                draft_source="ai",
                warnings=[],
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise OpenAICheckinDraftError("OpenAI check-in draft response was not valid") from exc

    def _build_request(self, text: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You organize one personal learning check-in into a concise structured draft. "
                                "Only classify subject as python, japanese, or sre. "
                                "Extract duration when explicitly present; otherwise choose a conservative estimate. "
                                "Only set difficulty and energy_level when clearly implied. "
                                "Do not invent achievements, tools, or outcomes not present in the user's text. "
                                "Use Traditional Chinese for assistant_note."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "learning_checkin_draft",
                    "strict": True,
                    "schema": self._response_schema(),
                }
            },
        }

    def _response_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "subject": {"type": "string", "enum": [subject.value for subject in LearningSubject]},
                "duration_minutes": {"type": "integer", "minimum": 1, "maximum": 1440},
                "summary": {"type": "string", "minLength": 1, "maxLength": 2000},
                "difficulty": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
                "energy_level": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 12,
                },
                "assistant_note": {"type": "string", "minLength": 1, "maxLength": 500},
            },
            "required": [
                "subject",
                "duration_minutes",
                "summary",
                "difficulty",
                "energy_level",
                "tags",
                "assistant_note",
            ],
        }

    def _extract_json(self, response_payload: dict[str, Any]) -> dict[str, Any]:
        output_text = response_payload.get("output_text")
        if isinstance(output_text, str):
            return json.loads(output_text)

        for item in response_payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return json.loads(content["text"])

        raise KeyError("No structured output text found")
