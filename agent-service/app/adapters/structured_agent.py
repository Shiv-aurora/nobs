from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from ..usage import ModelUsage, estimate_tokens
from .guard import PromptGuard


OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True)
class StructuredAgentResult:
    output: BaseModel
    usage: ModelUsage


class StructuredADKAgent:
    """One bounded Google ADK LlmAgent with typed input and output contracts."""

    def __init__(
        self,
        *,
        agent_id: str,
        model_name: str,
        instruction: str,
        output_schema: type[OutputT],
        prompt_guard: PromptGuard,
        max_output_tokens: int = 600,
        project_id: str = "",
        agent_engine_location: str = "",
        agent_engine_id: str = "",
    ) -> None:
        self.agent_id = agent_id
        self.model_name = model_name
        self.instruction = instruction
        self.output_schema = output_schema
        self.prompt_guard = prompt_guard
        self.max_output_tokens = max_output_tokens
        self.project_id = project_id
        self.agent_engine_location = agent_engine_location
        self.agent_engine_id = agent_engine_id

    async def run(self, payload: BaseModel | dict[str, object]) -> StructuredAgentResult:
        prompt = json.dumps(
            payload.model_dump(mode="json", exclude_none=True) if isinstance(payload, BaseModel) else payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=lambda value: value.isoformat() if hasattr(value, "isoformat") else str(value),
        )
        prompt_verdict = self.prompt_guard.screen_prompt(prompt)
        if not prompt_verdict.allowed:
            raise PermissionError(f"Model Armor blocked {self.agent_id} input: {prompt_verdict.reason}")

        try:
            from google.adk.agents import LlmAgent  # type: ignore[import-not-found]
            from google.adk.runners import Runner  # type: ignore[import-not-found]
            from google.adk.sessions import InMemorySessionService, VertexAiSessionService  # type: ignore[import-not-found]
            from google.genai import types  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - deployment-only path
            raise RuntimeError("Install noping-agent-service[google] to execute ADK missions") from exc

        agent = LlmAgent(
            name=self.agent_id.replace(":", "_").replace("-", "_"),
            model=self.model_name,
            instruction=self.instruction,
            output_schema=self.output_schema,
            output_key="structured_result",
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self.max_output_tokens,
                thinking_config=(
                    types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL)
                    if self.model_name.startswith("gemini-3")
                    else types.ThinkingConfig(thinking_budget=0)
                ),
            ),
        )
        session_service = (
            VertexAiSessionService(
                project=self.project_id,
                location=self.agent_engine_location,
                agent_engine_id=self.agent_engine_id,
            )
            if self.project_id and self.agent_engine_location and self.agent_engine_id
            else InMemorySessionService()
        )
        runner = Runner(agent=agent, app_name="nobs-meeting-missions", session_service=session_service)
        session_id = f"mission-agent-{uuid4().hex}"
        await session_service.create_session(app_name="nobs-meeting-missions", user_id="nobs-runtime", session_id=session_id)

        final_text = ""
        input_tokens = 0
        output_tokens = 0
        cached_tokens = 0
        async for event in runner.run_async(
            user_id="nobs-runtime",
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
        ):
            usage = getattr(event, "usage_metadata", None)
            if usage is not None:
                input_tokens = max(input_tokens, int(getattr(usage, "prompt_token_count", 0) or 0))
                output_tokens = max(
                    output_tokens,
                    int(getattr(usage, "candidates_token_count", 0) or 0)
                    + int(getattr(usage, "thoughts_token_count", 0) or 0),
                )
                cached_tokens = max(cached_tokens, int(getattr(usage, "cached_content_token_count", 0) or 0))
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(
                    part.text or "" for part in event.content.parts if getattr(part, "text", None)
                ).strip()
        if not final_text:
            raise RuntimeError(f"{self.agent_id} returned no structured output")
        response_verdict = self.prompt_guard.screen_response(final_text)
        if not response_verdict.allowed:
            raise PermissionError(f"Model Armor blocked {self.agent_id} output: {response_verdict.reason}")
        parsed = self.output_schema.model_validate_json(final_text)
        return StructuredAgentResult(
            output=parsed,
            usage=ModelUsage(
                model_name=self.model_name,
                calls=1,
                input_tokens=input_tokens or estimate_tokens(prompt + self.instruction),
                output_tokens=output_tokens or estimate_tokens(final_text),
                cached_input_tokens=cached_tokens,
            ),
        )
