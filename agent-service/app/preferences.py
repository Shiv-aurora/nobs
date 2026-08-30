from __future__ import annotations

import asyncio
import json
from typing import Literal

from pydantic import BaseModel, Field


class PreferenceWrite(BaseModel):
    actor_id: str
    key: Literal["brief_detail", "calendar_view", "digest_frequency", "timezone"]
    value: str = Field(min_length=1, max_length=100)


class PreferenceMemory:
    """Preference-only memory boundary that is never consulted for authority."""

    APP_NAME = "nobs-user-preferences"

    def __init__(self, *, project_id: str, location: str, agent_engine_id: str, demo_mode: bool):
        self.project_id = project_id
        self.location = location
        self.agent_engine_id = agent_engine_id
        self.demo_mode = demo_mode
        self.local: dict[tuple[str, str], str] = {}

    def write(self, preference: PreferenceWrite) -> dict[str, str]:
        if self.demo_mode or not self.agent_engine_id:
            self.local[(preference.actor_id, preference.key)] = preference.value
            return {"status": "stored", "backend": "local_test", "authority_effect": "none"}
        asyncio.run(self._write_vertex(preference))
        return {"status": "stored", "backend": "vertex_memory_bank", "authority_effect": "none"}

    async def _write_vertex(self, preference: PreferenceWrite) -> None:
        from google.adk.memory import VertexAiMemoryBankService
        from google.adk.memory.memory_entry import MemoryEntry
        from google.genai import types

        service = VertexAiMemoryBankService(
            project=self.project_id,
            location=self.location,
            agent_engine_id=self.agent_engine_id,
        )
        content = json.dumps({"preference_key": preference.key, "preference_value": preference.value}, separators=(",", ":"))
        await service.add_memory(
            app_name=self.APP_NAME,
            user_id=preference.actor_id,
            memories=[MemoryEntry(
                content=types.Content(role="user", parts=[types.Part(text=content)]),
                author=preference.actor_id,
                custom_metadata={
                    "category": "presentation_preference",
                    "authority_effect": False,
                    "source": "explicit_user_setting",
                },
            )],
            custom_metadata={"authority_effect": False},
        )
