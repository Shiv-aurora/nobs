from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any, TYPE_CHECKING

from ..models import AuditEvent, Decision, DecisionMemory, HandoffPacket, KnowledgeMemory, LiveMeetingSession, Meeting, MeetingDelegation, MeetingHandoff, MeetingPrepRun, OOOQueueItem, QueryResult, WorkEvent
from ..mission_models import AgentManifest, HumanCheckpoint, MissionRun, MissionStep, ProposedCommand
from .base import StateStore

if TYPE_CHECKING:
    from ..workspace import Workspace

logger = logging.getLogger(__name__)


class FirestoreStateStore(StateStore):
    """Firestore implementation for runtime state.

    Imports the Google client lazily so local tests do not need cloud packages.
    Documents are scoped under one organization root and large evidence bodies
    remain in Mattermost; query results store compact references and traces.
    """

    DYNAMIC_COLLECTIONS = ("queries", "decisions", "memories", "audit", "work_events", "meetings", "meeting_runs", "knowledge_memories", "ooo_queue", "handoff_packets", "meeting_delegations", "live_meeting_sessions", "meeting_handoffs", "missions", "mission_steps", "human_checkpoints", "commands", "agents")

    def __init__(self, *, project_id: str, database: str, organization_id: str):
        if not project_id:
            raise ValueError("GCP project ID is required for Firestore persistence")
        try:
            from google.cloud import firestore  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - exercised in deployment
            raise RuntimeError("Install noping-agent-service[google] for Firestore persistence") from exc
        self._firestore = firestore
        self.client = firestore.Client(project=project_id, database=database)
        self.organization_id = organization_id
        self.root = self.client.collection("organizations").document(organization_id)

    def _collection(self, name: str):
        return self.root.collection(name)

    @staticmethod
    def _payload(model: Any) -> dict[str, Any]:
        return model.model_dump(mode="json", exclude_none=True)

    def restore(self, workspace: "Workspace") -> None:
        for snapshot in self._collection("decisions").stream():
            decision = Decision.model_validate(snapshot.to_dict())
            workspace.decisions[decision.id] = decision
        for snapshot in self._collection("memories").stream():
            memory = DecisionMemory.model_validate(snapshot.to_dict())
            workspace.memories[memory.id] = memory
        for snapshot in self._collection("queries").order_by("created_at", direction=self._firestore.Query.DESCENDING).limit(100).stream():
            payload = snapshot.to_dict()
            for evidence in payload.get("evidence", []):
                evidence.setdefault("content", "[source body not persisted]")
            result = QueryResult.model_validate(payload)
            workspace.query_results[result.run_id] = result
        restored_audit = [AuditEvent.model_validate(snapshot.to_dict()) for snapshot in self._collection("audit").order_by("created_at").limit(500).stream()]
        workspace.audit.extend(restored_audit)
        for snapshot in self._collection("work_events").stream():
            event = WorkEvent.model_validate(snapshot.to_dict())
            workspace.work_events[event.id] = event
        for snapshot in self._collection("meetings").stream():
            meeting = Meeting.model_validate(snapshot.to_dict())
            workspace.meetings[meeting.id] = meeting
        for snapshot in self._collection("meeting_runs").stream():
            run = MeetingPrepRun.model_validate(snapshot.to_dict())
            workspace.meeting_runs[run.id] = run
        for snapshot in self._collection("knowledge_memories").stream():
            memory = KnowledgeMemory.model_validate(snapshot.to_dict())
            workspace.knowledge_memories[memory.id] = memory
        for snapshot in self._collection("ooo_queue").stream():
            item = OOOQueueItem.model_validate(snapshot.to_dict())
            workspace.ooo_queue[item.id] = item
        for snapshot in self._collection("handoff_packets").stream():
            packet = HandoffPacket.model_validate(snapshot.to_dict())
            workspace.handoff_packets[packet.id] = packet
        for snapshot in self._collection("meeting_delegations").stream():
            delegation = MeetingDelegation.model_validate(snapshot.to_dict())
            workspace.meeting_delegations[delegation.id] = delegation
        for snapshot in self._collection("live_meeting_sessions").stream():
            session = LiveMeetingSession.model_validate(snapshot.to_dict())
            workspace.live_meeting_sessions[session.id] = session
        for snapshot in self._collection("meeting_handoffs").stream():
            handoff = MeetingHandoff.model_validate(snapshot.to_dict())
            workspace.meeting_handoffs[handoff.id] = handoff
        for snapshot in self._collection("missions").stream():
            mission = MissionRun.model_validate(snapshot.to_dict())
            workspace.missions[mission.id] = mission
        for snapshot in self._collection("mission_steps").stream():
            step = MissionStep.model_validate(snapshot.to_dict())
            workspace.mission_steps[step.id] = step
        for snapshot in self._collection("human_checkpoints").stream():
            checkpoint = HumanCheckpoint.model_validate(snapshot.to_dict())
            workspace.human_checkpoints[checkpoint.id] = checkpoint
        for snapshot in self._collection("agents").stream():
            manifest = AgentManifest.model_validate(snapshot.to_dict())
            workspace.agent_manifests[f"{manifest.id}@{manifest.version}"] = manifest
        for snapshot in self._collection("commands").stream():
            command = ProposedCommand.model_validate(snapshot.to_dict())
            workspace.commands[command.id] = command
        stats = self.root.collection("config").document("stats").get()
        if stats.exists:
            workspace.stats.update({key: int(value) for key, value in stats.to_dict().items() if key in workspace.stats})

    def put_query_result(self, result: QueryResult) -> None:
        # Keep evidence references compact in durable query traces. Source bodies
        # remain authoritative in Mattermost or their source system.
        payload = self._payload(result)
        payload["evidence"] = [
            {
                "id": item.id,
                "title": item.title,
                "source_type": item.source_type,
                "source_url": item.source_url,
                "entity_ids": item.entity_ids,
                "scope": item.scope,
                "observed_at": item.observed_at.isoformat(),
                "confidence": item.confidence,
                "security_state": item.security_state.value,
                "security_reason": item.security_reason,
            }
            for item in result.evidence
        ]
        self._collection("queries").document(result.run_id).set(payload)

    def put_decision(self, decision: Decision) -> None:
        self._collection("decisions").document(decision.id).set(self._payload(decision))

    def put_memory(self, memory: DecisionMemory) -> None:
        self._collection("memories").document(memory.id).set(self._payload(memory))

    def append_audit(self, event: AuditEvent) -> None:
        self._collection("audit").document(event.id).set(self._payload(event))

    def put_work_event(self, event: WorkEvent) -> None:
        self._collection("work_events").document(event.id).create(self._payload(event))

    def put_stats(self, stats: dict[str, int]) -> None:
        self.root.collection("config").document("stats").set(stats, merge=True)

    def put_meeting(self, meeting: Meeting) -> None:
        self._collection("meetings").document(meeting.id).set(self._payload(meeting))

    def put_meeting_run(self, run: MeetingPrepRun) -> None:
        self._collection("meeting_runs").document(run.id).set(self._payload(run))

    def put_knowledge_memory(self, memory: KnowledgeMemory) -> None:
        self._collection("knowledge_memories").document(memory.id).set(self._payload(memory))

    def put_ooo_queue_item(self, item: OOOQueueItem) -> None:
        self._collection("ooo_queue").document(item.id).set(self._payload(item))

    def put_handoff_packet(self, packet: HandoffPacket) -> None:
        self._collection("handoff_packets").document(packet.id).set(self._payload(packet))

    def put_meeting_delegation(self, delegation: MeetingDelegation) -> None:
        self._collection("meeting_delegations").document(delegation.id).set(self._payload(delegation))

    def put_live_meeting_session(self, session: LiveMeetingSession) -> None:
        payload = self._payload(session)
        # Never persist binary media. The session contains counters and compact
        # semantic outcomes only.
        self._collection("live_meeting_sessions").document(session.id).set(payload)

    def put_meeting_handoff(self, handoff: MeetingHandoff) -> None:
        self._collection("meeting_handoffs").document(handoff.id).set(self._payload(handoff))

    def put_mission_transition(self, mission: MissionRun, step: MissionStep | None = None) -> None:
        transaction = self.client.transaction()

        @self._firestore.transactional
        def persist(txn) -> None:
            txn.set(self._collection("missions").document(mission.id), self._payload(mission))
            if step is not None:
                txn.set(self._collection("mission_steps").document(step.id), self._payload(step))

        persist(transaction)

    def put_checkpoint(self, checkpoint: HumanCheckpoint) -> None:
        self._collection("human_checkpoints").document(checkpoint.id).set(self._payload(checkpoint))

    def put_agent_manifest(self, manifest: AgentManifest) -> None:
        document_id = f"{manifest.id.replace(':', '-')}-{manifest.version}"
        self._collection("agents").document(document_id).set(self._payload(manifest))

    def put_command(self, command: ProposedCommand) -> None:
        self._collection("commands").document(command.id).set(self._payload(command))

    def clear_dynamic(self) -> None:
        for name in self.DYNAMIC_COLLECTIONS:
            self._delete_collection(self._collection(name))
        self.root.collection("config").document("stats").delete()

    def _delete_collection(self, collection, batch_size: int = 100) -> None:
        while True:
            documents: Iterable[Any] = collection.limit(batch_size).stream()
            documents = list(documents)
            if not documents:
                return
            batch = self.client.batch()
            for document in documents:
                batch.delete(document.reference)
            batch.commit()

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if close:
            close()
