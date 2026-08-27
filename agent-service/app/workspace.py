from __future__ import annotations

import copy
import json
from pathlib import Path
from threading import RLock
from typing import Any

from .models import AuditEvent, Decision, DecisionMemory, Evidence, Policy, Project, QueryResult, Team, User, WorkEvent, WorkItem, Delegation
from .persistence.base import NullStateStore, StateStore


class Workspace:
    """Thread-safe organizational state with a pluggable durable runtime store."""

    def __init__(self, source_path: Path, state_store: StateStore | None = None):
        self.source_path = source_path
        self.lock = RLock()
        self.state_store = state_store or NullStateStore()
        self.reset(load_persisted=True)

    def reset(self, *, load_persisted: bool = True) -> None:
        payload = json.loads(self.source_path.read_text())
        with self.lock:
            self.organization: dict[str, Any] = payload["organization"]
            self.users = {item["id"]: User.model_validate(item) for item in payload["users"]}
            self.teams = {item["id"]: Team.model_validate(item) for item in payload["teams"]}
            self.projects = {item["id"]: Project.model_validate(item) for item in payload["projects"]}
            self.work_items = {item["id"]: WorkItem.model_validate(item) for item in payload["work_items"]}
            self.policies = {item["id"]: Policy.model_validate(item) for item in payload["policies"]}
            self.delegations = {item["id"]: Delegation.model_validate(item) for item in payload["delegations"]}
            self.evidence = {item["id"]: Evidence.model_validate(item) for item in payload["evidence"]}
            self.work_events = {item["id"]: WorkEvent.model_validate(item) for item in payload["work_events"]}
            self.decisions: dict[str, Decision] = {}
            self.memories: dict[str, DecisionMemory] = {}
            self.audit: list[AuditEvent] = []
            self.query_results: dict[str, QueryResult] = {}
            self.stats = {
                "queries_total": 0,
                "resolved_without_human": 0,
                "human_interruptions": 0,
                "restricted_requests_blocked": 0,
                "poisoned_sources_blocked": 0,
                "cache_hits": 0,
            }
            if load_persisted:
                self.state_store.restore(self)

    def reset_demo(self) -> None:
        self.state_store.clear_dynamic()
        self.reset(load_persisted=False)

    def save_query_result(self, result: QueryResult) -> None:
        with self.lock:
            self.query_results[result.run_id] = result
        self.state_store.put_query_result(result)

    def save_decision(self, decision: Decision) -> None:
        with self.lock:
            self.decisions[decision.id] = decision
        self.state_store.put_decision(decision)

    def save_memory(self, memory: DecisionMemory) -> None:
        with self.lock:
            self.memories[memory.id] = memory
        self.state_store.put_memory(memory)

    def append_audit(self, event: AuditEvent) -> None:
        with self.lock:
            self.audit.append(event)
        self.state_store.append_audit(event)

    def save_work_event(self, event: WorkEvent) -> bool:
        with self.lock:
            if event.id in self.work_events:
                return False
            self.work_events[event.id] = event
        self.state_store.put_work_event(event)
        return True

    def increment_stat(self, key: str, amount: int = 1) -> None:
        with self.lock:
            self.stats[key] = self.stats.get(key, 0) + amount
            snapshot = self.stats.copy()
        self.state_store.put_stats(snapshot)

    def persist_stats(self) -> None:
        self.state_store.put_stats(self.stats.copy())

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return copy.deepcopy({
                "organization": self.organization,
                "users": self.users,
                "teams": self.teams,
                "projects": self.projects,
                "work_items": self.work_items,
                "policies": self.policies,
                "delegations": self.delegations,
                "evidence": self.evidence,
                "work_events": self.work_events,
                "decisions": self.decisions,
                "memories": self.memories,
                "audit": self.audit,
                "query_results": self.query_results,
                "stats": self.stats,
            })
