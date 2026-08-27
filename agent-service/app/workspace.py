from __future__ import annotations

import copy
import json
from pathlib import Path
from threading import RLock
from typing import Any

from .models import Delegation, Decision, DecisionMemory, Evidence, Policy, Project, Team, User, WorkEvent, WorkItem


class Workspace:
    """Thread-safe demo persistence with the same contracts as the Firestore adapter."""

    def __init__(self, source_path: Path):
        self.source_path = source_path
        self.lock = RLock()
        self.reset()

    def reset(self) -> None:
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
            self.audit: list[Any] = []
            self.query_results: dict[str, Any] = {}
            self.stats = {
                "queries_total": 0,
                "resolved_without_human": 0,
                "human_interruptions": 0,
                "restricted_requests_blocked": 0,
                "poisoned_sources_blocked": 0,
                "cache_hits": 0,
            }

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
