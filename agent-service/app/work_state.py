from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from .models import Project, SemanticWorkState, WorkEvent, WorkItem
from .workspace import Workspace


_TERMINAL_WORK_STATUSES = {"done", "closed", "merged", "approved", "ready_to_merge", "released"}


class WorkStateProjector:
    """Project normalized activity into a compact, permission-neutral work map.

    Connectors emit one WorkEvent contract. This projector intentionally does not
    know GitHub, Calendar, or Jira API shapes; it only understands normalized event
    types and entity relationships from the organizational model. That keeps the
    semantic state layer useful when a company swaps tools.
    """

    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    @staticmethod
    def _latest(events: Iterable[WorkEvent]) -> WorkEvent | None:
        values = list(events)
        return max(values, key=lambda item: item.occurred_at) if values else None

    def _actor_state(self, actor_id: str, events: list[WorkEvent]) -> SemanticWorkState | None:
        user = self.workspace.users.get(actor_id)
        latest = self._latest(events)
        if not user or latest is None:
            return None

        calendar_events = [event for event in events if event.event_type.startswith("calendar.out_of_office")]
        latest_calendar = self._latest(calendar_events)
        if latest_calendar and latest_calendar.event_type == "calendar.out_of_office.ended":
            return SemanticWorkState(
                entity_id=user.id,
                entity_type="person",
                headline=f"{user.name} is available",
                detail="Their out-of-office delegation window has ended.",
                status="available",
                confidence=1.0,
                source_event_ids=[event.id for event in calendar_events],
                updated_at=latest_calendar.occurred_at,
            )

        if user.availability.status == "out_of_office" and latest_calendar:
            delegate_id = latest_calendar.payload.get("delegate_user_id") or user.availability.delegate_user_id
            delegate = self.workspace.users.get(str(delegate_id)) if delegate_id else None
            until = latest_calendar.payload.get("until")
            if delegate:
                headline = f"{user.name} is out; {delegate.name} holds delegated authority"
                detail = f"The active delegation remains valid until {until}." if until else "An approved delegate is active."
                status = "delegated"
            else:
                headline = f"{user.name} is out of office"
                detail = f"Expected back {until}." if until else "No return time is available."
                status = "out_of_office"
            return SemanticWorkState(
                entity_id=user.id,
                entity_type="person",
                headline=headline,
                detail=detail,
                status=status,
                confidence=1.0,
                source_event_ids=[event.id for event in calendar_events],
                updated_at=latest_calendar.occurred_at,
            )

        work_item = self._work_item_from_event(latest)
        if latest.event_type.startswith("pull_request.") and work_item:
            review_state = str(latest.payload.get("review_state", "awaiting_review"))
            number = latest.payload.get("number")
            if review_state in {"approved", "changes_approved"}:
                headline = f"{work_item.key} is approved and ready to merge"
                status = "ready_to_merge"
                detail = f"{user.name}'s {work_item.title.lower()} passed review."
            else:
                headline = f"{user.name}'s {work_item.key} work is in review"
                status = "in_review"
                checks_passed = latest.payload.get("checks_passed")
                check_summary = f"{checks_passed} checks passed" if checks_passed is not None else "Automated checks are available"
                pr_summary = f"PR #{number}" if number is not None else "The pull request"
                detail = f"{pr_summary}: {check_summary}; review state is {review_state.replace('_', ' ')}."
            return SemanticWorkState(
                entity_id=user.id,
                entity_type="person",
                headline=headline,
                detail=detail,
                status=status,
                confidence=0.99,
                source_event_ids=[event.id for event in events],
                updated_at=latest.occurred_at,
            )

        if latest.event_type == "issue.status_changed" and work_item:
            status = str(latest.payload.get("to", work_item.status))
            return SemanticWorkState(
                entity_id=user.id,
                entity_type="person",
                headline=f"{user.name} moved {work_item.key} to {status.replace('_', ' ')}",
                detail=work_item.title,
                status=status,
                confidence=0.98,
                source_event_ids=[event.id for event in events],
                updated_at=latest.occurred_at,
            )

        return SemanticWorkState(
            entity_id=user.id,
            entity_type="person",
            headline=f"{user.name} has recent activity",
            detail=f"Latest signal: {latest.event_type.replace('.', ' ')} from {latest.source}.",
            status="active",
            confidence=0.8,
            source_event_ids=[event.id for event in events],
            updated_at=latest.occurred_at,
        )

    def _work_item_from_event(self, event: WorkEvent) -> WorkItem | None:
        for entity_id in event.entity_ids:
            item = self.workspace.work_items.get(entity_id)
            if item:
                return item
        return None

    def _project_state(self, project: Project, events: list[WorkEvent]) -> SemanticWorkState:
        latest = self._latest(events)
        blockers = [self.workspace.work_items[item_id] for item_id in project.blocker_ids if item_id in self.workspace.work_items]
        open_blockers = [item for item in blockers if item.status.lower() not in _TERMINAL_WORK_STATUSES]

        if open_blockers:
            blocker = max(open_blockers, key=lambda item: item.updated_at)
            owner = self.workspace.users.get(blocker.owner_user_id)
            owner_name = owner.name if owner else blocker.owner_user_id
            headline = f"{project.name} is blocked by {blocker.key}"
            detail = f"{blocker.title}. Owner: {owner_name}; status: {blocker.status.replace('_', ' ')}."
            status = "blocked"
            confidence = 0.97
        elif blockers:
            headline = f"{project.name} cleared its recorded blockers"
            detail = "All modeled launch blockers are in a terminal state; final release verification is still required."
            status = "ready_for_verification"
            confidence = 0.95
        else:
            headline = f"{project.name} is {project.status.replace('_', ' ')}"
            detail = project.summary
            status = project.status
            confidence = 0.9

        source_ids = [event.id for event in events]
        updated_at = latest.occurred_at if latest else max(
            (item.updated_at for item in blockers),
            default=datetime.fromisoformat(f"{project.target_date}T00:00:00+00:00"),
        )
        return SemanticWorkState(
            entity_id=project.id,
            entity_type="project",
            headline=headline,
            detail=detail,
            status=status,
            confidence=confidence,
            source_event_ids=source_ids,
            updated_at=updated_at,
        )

    def project(self) -> list[SemanticWorkState]:
        events_by_actor: dict[str, list[WorkEvent]] = defaultdict(list)
        events_by_entity: dict[str, list[WorkEvent]] = defaultdict(list)
        for event in self.workspace.work_events.values():
            events_by_actor[event.actor_user_id].append(event)
            for entity_id in event.entity_ids:
                events_by_entity[entity_id].append(event)

        states: list[SemanticWorkState] = []
        for actor_id, events in events_by_actor.items():
            state = self._actor_state(actor_id, sorted(events, key=lambda item: item.occurred_at))
            if state:
                states.append(state)

        for project in self.workspace.projects.values():
            states.append(self._project_state(project, events_by_entity.get(project.id, [])))

        return sorted(states, key=lambda item: (item.entity_type, item.entity_id))

    def ingest(self, event: WorkEvent) -> bool:
        if not self.workspace.save_work_event(event):
            return False

        user = self.workspace.users.get(event.actor_user_id)
        if user and event.event_type == "calendar.out_of_office.ended":
            user.availability.status = "available"
            user.availability.until = None
            user.availability.delegate_user_id = None
        elif user and event.event_type == "calendar.out_of_office":
            user.availability.status = "out_of_office"
            until = event.payload.get("until")
            user.availability.until = datetime.fromisoformat(str(until)) if until else None
            user.availability.delegate_user_id = event.payload.get("delegate_user_id")

        work_item = self._work_item_from_event(event)
        if work_item and event.event_type == "issue.status_changed":
            work_item.status = str(event.payload.get("to", work_item.status))
            work_item.updated_at = event.occurred_at
        elif work_item and event.event_type.startswith("pull_request."):
            review_state = str(event.payload.get("review_state", ""))
            if review_state in {"approved", "changes_approved"}:
                work_item.status = "ready_to_merge"
            elif event.event_type in {"pull_request.opened", "pull_request.synchronize", "pull_request.reviewed"}:
                work_item.status = "in_review"
            work_item.updated_at = event.occurred_at
        return True
