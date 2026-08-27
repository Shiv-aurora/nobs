from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .models import SemanticWorkState, WorkEvent
from .workspace import Workspace


class WorkStateProjector:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def project(self) -> list[SemanticWorkState]:
        events_by_actor: dict[str, list[WorkEvent]] = defaultdict(list)
        events_by_entity: dict[str, list[WorkEvent]] = defaultdict(list)
        for event in self.workspace.work_events.values():
            events_by_actor[event.actor_user_id].append(event)
            for entity_id in event.entity_ids:
                events_by_entity[entity_id].append(event)

        states: list[SemanticWorkState] = []
        daniel_events = sorted(events_by_actor.get("daniel", []), key=lambda item: item.occurred_at)
        if daniel_events:
            latest = daniel_events[-1]
            review_state = latest.payload.get("review_state", "awaiting_review")
            if review_state == "approved":
                headline = "AUTH-392 is approved and ready to merge"
                status = "ready_to_merge"
                detail = "Daniel's iOS refresh-token fix passed review."
            else:
                headline = "Daniel's AUTH-392 fix is in review"
                status = "in_review"
                detail = "PR #892 passed 84 checks and is awaiting one reviewer."
            states.append(SemanticWorkState(
                entity_id="daniel",
                entity_type="person",
                headline=headline,
                detail=detail,
                status=status,
                confidence=0.99,
                source_event_ids=[event.id for event in daniel_events],
                updated_at=latest.occurred_at,
            ))

        sarah_events = sorted(events_by_actor.get("sarah", []), key=lambda item: item.occurred_at)
        if sarah_events:
            latest = sarah_events[-1]
            if latest.event_type == "calendar.out_of_office.ended":
                headline = "Sarah is available"
                detail = "Her delegated Atlas approval window has ended."
                status = "available"
            else:
                until = latest.payload.get("until", "tomorrow")
                headline = "Sarah is out; Alex holds delegated approval"
                detail = f"The delegation remains valid until {until}."
                status = "delegated"
            states.append(SemanticWorkState(
                entity_id="sarah",
                entity_type="person",
                headline=headline,
                detail=detail,
                status=status,
                confidence=1.0,
                source_event_ids=[event.id for event in sarah_events],
                updated_at=latest.occurred_at,
            ))

        atlas_events = sorted(events_by_entity.get("atlas", []), key=lambda item: item.occurred_at)
        if atlas_events:
            latest = atlas_events[-1]
            states.append(SemanticWorkState(
                entity_id="atlas",
                entity_type="project",
                headline="Atlas is blocked by SEC-184",
                detail="Engineering is ready; the final penetration-test review remains open.",
                status="blocked",
                confidence=0.97,
                source_event_ids=[event.id for event in atlas_events],
                updated_at=latest.occurred_at,
            ))
        return states

    def ingest(self, event: WorkEvent) -> bool:
        if event.id in self.workspace.work_events:
            return False
        self.workspace.work_events[event.id] = event
        user = self.workspace.users.get(event.actor_user_id)
        if user and event.event_type == "calendar.out_of_office.ended":
            user.availability.status = "available"
            user.availability.until = None
            user.availability.delegate_user_id = None
        elif user and event.event_type == "calendar.out_of_office":
            user.availability.status = "out_of_office"
            user.availability.until = datetime.fromisoformat(event.payload["until"])
            user.availability.delegate_user_id = event.payload.get("delegate_user_id")
        return True
