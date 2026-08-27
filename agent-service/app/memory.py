from __future__ import annotations

from datetime import timedelta

from .models import Decision, DecisionMemory
from .workspace import Workspace


class DecisionMemoryStore:
    def __init__(self, workspace: Workspace, now_fn):
        self.workspace = workspace
        self.now_fn = now_fn

    def find_valid(self, canonical_key: str, project_id: str | None, facts_hash: str) -> DecisionMemory | None:
        now = self.now_fn()
        for memory in self.workspace.memories.values():
            if (
                memory.canonical_key == canonical_key
                and memory.project_id == project_id
                and memory.facts_hash == facts_hash
                and memory.expires_at > now
            ):
                return memory
        return None

    def remember(self, decision: Decision) -> DecisionMemory:
        if not decision.resolved_by or not decision.rationale:
            raise ValueError("resolved decision required")
        memory = DecisionMemory(
            canonical_key=decision.canonical_key,
            project_id=decision.project_id,
            outcome=decision.status.value,
            rationale=decision.rationale,
            decided_by=decision.resolved_by,
            source_decision_id=decision.id,
            facts_hash=decision.facts_hash,
            created_at=self.now_fn(),
            expires_at=self.now_fn() + timedelta(hours=24),
        )
        self.workspace.save_memory(memory)
        return memory
