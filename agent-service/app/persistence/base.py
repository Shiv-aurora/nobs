from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from ..models import AuditEvent, Decision, DecisionMemory, QueryResult, WorkEvent

if TYPE_CHECKING:
    from ..workspace import Workspace


class StateStore(ABC):
    """Durability boundary for mutable organizational state.

    Static identity/project/policy seed data is loaded separately. This port only
    owns runtime state so the orchestration and policy layers stay independent of
    Firestore and can be tested deterministically.
    """

    @abstractmethod
    def restore(self, workspace: "Workspace") -> None:
        raise NotImplementedError

    @abstractmethod
    def put_query_result(self, result: QueryResult) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_decision(self, decision: Decision) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_memory(self, memory: DecisionMemory) -> None:
        raise NotImplementedError

    @abstractmethod
    def append_audit(self, event: AuditEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_work_event(self, event: WorkEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_stats(self, stats: dict[str, int]) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear_dynamic(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return None


class NullStateStore(StateStore):
    """No-op adapter used by local deterministic tests and the demo harness."""

    def restore(self, workspace: "Workspace") -> None:
        return None

    def put_query_result(self, result: QueryResult) -> None:
        return None

    def put_decision(self, decision: Decision) -> None:
        return None

    def put_memory(self, memory: DecisionMemory) -> None:
        return None

    def append_audit(self, event: AuditEvent) -> None:
        return None

    def put_work_event(self, event: WorkEvent) -> None:
        return None

    def put_stats(self, stats: dict[str, int]) -> None:
        return None

    def clear_dynamic(self) -> None:
        return None


class RecordingStateStore(NullStateStore):
    """Test double that records durability calls without external dependencies."""

    def __init__(self) -> None:
        self.operations: list[tuple[str, Any]] = []

    def put_query_result(self, result: QueryResult) -> None:
        self.operations.append(("query", result.run_id))

    def put_decision(self, decision: Decision) -> None:
        self.operations.append(("decision", decision.id))

    def put_memory(self, memory: DecisionMemory) -> None:
        self.operations.append(("memory", memory.id))

    def append_audit(self, event: AuditEvent) -> None:
        self.operations.append(("audit", event.id))

    def put_work_event(self, event: WorkEvent) -> None:
        self.operations.append(("work_event", event.id))

    def put_stats(self, stats: dict[str, int]) -> None:
        self.operations.append(("stats", stats.copy()))

    def clear_dynamic(self) -> None:
        self.operations.append(("clear", None))
