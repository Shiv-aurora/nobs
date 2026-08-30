from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from ..models import AuditEvent, Decision, DecisionMemory, HandoffPacket, KnowledgeMemory, LiveMeetingSession, Meeting, MeetingDelegation, MeetingHandoff, MeetingPrepRun, OOOQueueItem, QueryResult, WorkEvent
from ..mission_models import AgentManifest, HumanCheckpoint, MissionRun, MissionStep, ProposedCommand

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
    def put_meeting(self, meeting: Meeting) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_meeting_run(self, run: MeetingPrepRun) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_knowledge_memory(self, memory: KnowledgeMemory) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_ooo_queue_item(self, item: OOOQueueItem) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_handoff_packet(self, packet: HandoffPacket) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_meeting_delegation(self, delegation: MeetingDelegation) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_live_meeting_session(self, session: LiveMeetingSession) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_meeting_handoff(self, handoff: MeetingHandoff) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_mission_transition(self, mission: MissionRun, step: MissionStep | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_checkpoint(self, checkpoint: HumanCheckpoint) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_agent_manifest(self, manifest: AgentManifest) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_command(self, command: ProposedCommand) -> None:
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

    def put_meeting(self, meeting: Meeting) -> None:
        return None

    def put_meeting_run(self, run: MeetingPrepRun) -> None:
        return None

    def put_knowledge_memory(self, memory: KnowledgeMemory) -> None:
        return None

    def put_ooo_queue_item(self, item: OOOQueueItem) -> None:
        return None

    def put_handoff_packet(self, packet: HandoffPacket) -> None:
        return None

    def put_meeting_delegation(self, delegation: MeetingDelegation) -> None:
        return None

    def put_live_meeting_session(self, session: LiveMeetingSession) -> None:
        return None

    def put_meeting_handoff(self, handoff: MeetingHandoff) -> None:
        return None

    def put_mission_transition(self, mission: MissionRun, step: MissionStep | None = None) -> None:
        return None

    def put_checkpoint(self, checkpoint: HumanCheckpoint) -> None:
        return None

    def put_agent_manifest(self, manifest: AgentManifest) -> None:
        return None

    def put_command(self, command: ProposedCommand) -> None:
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

    def put_handoff_packet(self, packet: HandoffPacket) -> None:
        self.operations.append(("handoff_packet", packet.id))

    def put_meeting_delegation(self, delegation: MeetingDelegation) -> None:
        self.operations.append(("meeting_delegation", delegation.id))

    def put_live_meeting_session(self, session: LiveMeetingSession) -> None:
        self.operations.append(("live_meeting_session", session.id))

    def put_meeting_handoff(self, handoff: MeetingHandoff) -> None:
        self.operations.append(("meeting_handoff", handoff.id))

    def put_mission_transition(self, mission: MissionRun, step: MissionStep | None = None) -> None:
        self.operations.append(("mission_transition", (mission.id, step.id if step else None)))

    def put_checkpoint(self, checkpoint: HumanCheckpoint) -> None:
        self.operations.append(("checkpoint", checkpoint.id))

    def put_agent_manifest(self, manifest: AgentManifest) -> None:
        self.operations.append(("agent_manifest", f"{manifest.id}@{manifest.version}"))

    def put_command(self, command: ProposedCommand) -> None:
        self.operations.append(("command", command.id))

    def put_meeting(self, meeting: Meeting) -> None:
        self.operations.append(("meeting", meeting.id))

    def put_meeting_run(self, run: MeetingPrepRun) -> None:
        self.operations.append(("meeting_run", run.id))

    def put_knowledge_memory(self, memory: KnowledgeMemory) -> None:
        self.operations.append(("knowledge_memory", memory.id))

    def put_ooo_queue_item(self, item: OOOQueueItem) -> None:
        self.operations.append(("ooo_queue", item.id))

    def clear_dynamic(self) -> None:
        self.operations.append(("clear", None))
