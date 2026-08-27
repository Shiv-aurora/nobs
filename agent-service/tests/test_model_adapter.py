from __future__ import annotations

from types import SimpleNamespace

from app.adapters.model import GoogleADKModel
from app.models import Evidence, Intent


class FakeSessionService:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, str]] = []

    async def create_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        self.created.append((app_name, user_id, session_id))


class FakeEvent:
    def __init__(self, *, text: str = "", final: bool = False, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.content = SimpleNamespace(parts=[SimpleNamespace(text=text)]) if text else None
        self.usage_metadata = SimpleNamespace(
            prompt_token_count=input_tokens,
            candidates_token_count=output_tokens,
            cached_content_token_count=7,
        )
        self._final = final

    def is_final_response(self) -> bool:
        return self._final


class FakeRunner:
    def __init__(self) -> None:
        self.messages: list[object] = []

    async def run_async(self, *, user_id: str, session_id: str, new_message: object):
        self.messages.append(new_message)
        yield FakeEvent(input_tokens=321, output_tokens=0)
        yield FakeEvent(text="Atlas is blocked by SEC-184.", final=True, input_tokens=321, output_tokens=18)


def evidence() -> list[Evidence]:
    return [
        Evidence.model_validate(
            {
                "id": "ev-1",
                "title": "Security review",
                "source_type": "mattermost",
                "source_url": "https://example.test/sec-184",
                "entity_ids": ["atlas", "sec-184"],
                "scope": "project",
                "content": "SEC-184 remains pending.",
                "observed_at": "2026-08-27T12:00:00-04:00",
                "confidence": 0.98,
            }
        )
    ]


def test_google_adk_adapter_executes_runner_and_collects_usage() -> None:
    runner = FakeRunner()
    sessions = FakeSessionService()

    def factory():
        return runner, sessions, lambda value: {"role": "user", "text": value}

    adapter = GoogleADKModel(model_name="gemini-3.5-flash", runner_factory=factory)
    result = adapter.synthesize(text="Why is Atlas blocked?", intent=Intent.FACTUAL, evidence=evidence())

    assert result.text == "Atlas is blocked by SEC-184."
    assert result.usage.model_name == "gemini-3.5-flash"
    assert result.usage.input_tokens == 321
    assert result.usage.output_tokens == 18
    assert result.usage.cached_input_tokens == 7
    assert len(sessions.created) == 1
    assert '"question":"Why is Atlas blocked?"' in runner.messages[0]["text"]
    assert "SEC-184 remains pending" in runner.messages[0]["text"]


def test_google_adk_adapter_falls_back_to_conservative_usage_estimate() -> None:
    class NoUsageRunner:
        async def run_async(self, **kwargs):
            yield FakeEvent(text="Safe answer.", final=True)

    sessions = FakeSessionService()
    adapter = GoogleADKModel(
        runner_factory=lambda: (NoUsageRunner(), sessions, lambda value: value),
    )
    result = adapter.synthesize(text="Why?", intent=Intent.FACTUAL, evidence=evidence())
    assert result.usage.input_tokens > 0
    assert result.usage.output_tokens > 0
