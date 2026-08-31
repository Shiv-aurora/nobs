from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256

from .mission_models import MissionCheckpointResolution
from .models import (
    AgendaItem,
    AuditEvent,
    Meeting,
    MeetingActionRequest,
    MeetingAttendee,
    MeetingPrepRun,
    WorkEvent,
)
from .workspace import Workspace


class MeetingService:
    """Permission-aware meeting preparation over compact Calendar projections.

    Calendar remains the source of truth. The service stores only the fields that
    power preparation and the resulting brief; connector-specific reads/writes
    stay in the trusted Mattermost plugin boundary.
    """

    def __init__(self, workspace: Workspace, now_fn):
        self.workspace = workspace
        self.now_fn = now_fn
        self.mission_runtime = None
        # Live Calendar projections and canonical demo proof cases coexist.
        # Restore only missing fixtures so persisted preparation state and
        # externally sourced meetings are never overwritten.
        for meeting in self._demo_meetings():
            if meeting.id not in self.workspace.meetings:
                self.workspace.meetings[meeting.id] = meeting
        # Narrow fixture migration: an older persisted Atlas demo meeting may
        # predate the explicit authority contract. Preserve all other state.
        launch = self.workspace.meetings.get("meeting-atlas-launch-readiness")
        security_item = next((item for item in launch.agenda if item.id == "launch-security"), None) if launch else None
        if launch and security_item and not security_item.authority_type:
            security_item.authority_type = "atlas_security_approval"
            self.workspace.save_meeting(launch)

    def reset_demo(self) -> None:
        self.workspace.meetings.clear()
        self.workspace.meeting_runs.clear()
        self.workspace.knowledge_memories.clear()
        self.workspace.ooo_queue.clear()
        for meeting in self._demo_meetings():
            self.workspace.meetings[meeting.id] = meeting

    def _person(self, user_id: str, fallback: tuple[str, str]) -> MeetingAttendee:
        person = self.workspace.users.get(user_id)
        return MeetingAttendee(
            user_id=user_id,
            name=person.name if person else fallback[0],
            role=person.title if person else fallback[1],
        )

    def _demo_meetings(self) -> list[Meeting]:
        now = self.now_fn().replace(minute=0, second=0, microsecond=0)
        attendees = [
            self._person("shivam", ("Shivam Arora", "Engineering Lead")),
            self._person("maya", ("Maya Patel", "Pricing & Launch Operations")),
            self._person("daniel", ("Daniel Kim", "Mobile Engineer")),
            self._person("sarah", ("Sarah Chen", "Security Lead")),
            self._person("priya", ("Priya Shah", "Senior Product Manager")),
            self._person("alex", ("Alex Morgan", "Staff Security Engineer")),
        ]
        engineering_start = now + timedelta(days=1, hours=2)
        support_start = now + timedelta(days=1, hours=4)
        relay_start = now + timedelta(days=1, hours=6)
        launch_start = now + timedelta(days=2, hours=3)
        pricing_start = now + timedelta(days=2, hours=5)
        welcome_start = now + timedelta(days=3, hours=1)
        onboarding_start = now + timedelta(days=3, hours=3)
        mobile_release_start = now + timedelta(days=4, hours=2)
        operating_review_start = now + timedelta(days=5, hours=2)
        return [
            Meeting(
                id="meeting-atlas-engineering-sync",
                calendar_event_id="demo-atlas-engineering-sync",
                title="Atlas engineering sync",
                description="AUTH-392 readiness, integration checks, and release ownership.",
                start_at=engineering_start,
                end_at=engineering_start + timedelta(minutes=30),
                organizer_user_id="shivam",
                attendee_user_ids=["shivam", "maya", "daniel", "priya"],
                attendees=[attendees[0], attendees[1], attendees[2], attendees[4]],
                agenda=[
                    AgendaItem(id="eng-auth", title="Confirm AUTH-392 readiness", owner_user_id="daniel"),
                    AgendaItem(id="eng-tests", title="Verify mobile integration results", owner_user_id="daniel"),
                    AgendaItem(id="eng-owner", title="Confirm release ownership", owner_user_id="priya"),
                ],
                preparation_eligibility="eligible",
                preparation_reason="Project status meeting with an actionable engineering agenda.",
                workroom_channel="agent-workroom-atlas",
                etag="demo-eng-v1",
                updated_at=now,
            ),
            Meeting(
                id="meeting-northstar-escalation-review",
                calendar_event_id="demo-northstar-escalation-review",
                title="Northstar escalation review",
                description="Customer-safe Atlas status and the open delivery questions for Northstar.",
                start_at=engineering_start + timedelta(minutes=5),
                end_at=engineering_start + timedelta(minutes=35),
                organizer_user_id="maya",
                attendee_user_ids=["shivam", "maya", "priya"],
                attendees=[attendees[0], attendees[1], attendees[4]],
                agenda=[
                    AgendaItem(id="northstar-status", title="Share the latest customer-safe Atlas status", owner_user_id="maya"),
                    AgendaItem(id="northstar-question", title="Bring back any delivery question that needs Shivam", owner_user_id="shivam"),
                ],
                preparation_eligibility="eligible",
                preparation_reason="Work meeting that overlaps the engineering sync and can accept a bounded representative mission.",
                workroom_channel="agent-workroom-atlas",
                etag="demo-northstar-v1",
                updated_at=now,
            ),
            Meeting(
                id="meeting-atlas-launch-readiness",
                calendar_event_id="demo-atlas-launch-readiness",
                title="Atlas launch readiness",
                description="Resolve launch blockers and decide whether the Northstar timing exception can proceed.",
                start_at=launch_start,
                end_at=launch_start + timedelta(minutes=60),
                organizer_user_id="shivam",
                attendee_user_ids=[item.user_id for item in attendees],
                attendees=attendees,
                agenda=[
                    AgendaItem(id="launch-engineering", title="Engineering readiness", owner_user_id="daniel"),
                    AgendaItem(id="launch-customer", title="Northstar customer impact", owner_user_id="maya"),
                    AgendaItem(
                        id="launch-security",
                        title="Security exception decision",
                        owner_user_id="sarah",
                        authority_type="atlas_security_approval",
                    ),
                ],
                preparation_eligibility="eligible",
                preparation_reason="Cross-functional launch meeting with one authority-bound decision.",
                workroom_channel="agent-workroom-atlas",
                etag="demo-launch-v1",
                updated_at=now,
            ),
            Meeting(
                id="meeting-support-taxonomy-signoff",
                calendar_event_id="demo-support-taxonomy-signoff",
                title="Support taxonomy sign-off",
                description="Review the agent-produced reporting crosswalk and resolve one customer-facing label.",
                start_at=support_start,
                end_at=support_start + timedelta(minutes=30),
                organizer_user_id="maya",
                attendee_user_ids=["maya", "priya", "shivam"],
                attendees=[attendees[1], attendees[4], attendees[0]],
                agenda=[
                    AgendaItem(id="taxonomy-validation", title="Review 34 completed validation checks", owner_user_id="maya"),
                    AgendaItem(id="taxonomy-label", title="Choose the final customer-facing availability label", owner_user_id="maya"),
                    AgendaItem(id="taxonomy-rollout", title="Confirm reporting crosswalk rollout owner", owner_user_id="shivam"),
                ],
                preparation_eligibility="eligible",
                preparation_reason="Bounded review meeting with completed agent work and one human language decision.",
                workroom_channel="agent-workroom-support-taxonomy",
                etag="demo-taxonomy-v1",
                updated_at=now,
            ),
            Meeting(
                id="meeting-relay-offline-recovery",
                calendar_event_id="demo-relay-offline-recovery",
                title="Relay offline recovery rehearsal",
                description="Validate the 48-hour recovery path, duplicate-event guard, and rollout ownership for Project Relay.",
                start_at=relay_start,
                end_at=relay_start + timedelta(minutes=45),
                organizer_user_id="shivam",
                attendee_user_ids=["shivam", "maya", "daniel", "priya"],
                attendees=[attendees[0], attendees[1], attendees[2], attendees[4]],
                agenda=[
                    AgendaItem(id="relay-recovery", title="Review the 48-hour offline recovery result", owner_user_id="daniel"),
                    AgendaItem(id="relay-duplicates", title="Confirm duplicate-event protection", owner_user_id="daniel"),
                    AgendaItem(id="relay-rollout", title="Assign staged rollout and rollback owners", owner_user_id="shivam"),
                ],
                preparation_eligibility="eligible",
                preparation_reason="Engineering rehearsal whose evidence and ownership can be prepared before humans join.",
                workroom_channel="agent-workroom-mobile-release-notes",
                etag="demo-relay-v1",
                updated_at=now,
            ),
            Meeting(
                id="meeting-pricing-faq-approval",
                calendar_event_id="demo-pricing-faq-approval",
                title="Pricing launch FAQ approval",
                description="Approve the bounded pre-work brief before agents generate and publish customer-safe enablement material.",
                start_at=pricing_start,
                end_at=pricing_start + timedelta(minutes=30),
                organizer_user_id="priya",
                attendee_user_ids=["maya", "priya", "shivam"],
                attendees=[attendees[1], attendees[4], attendees[0]],
                agenda=[
                    AgendaItem(id="pricing-scope", title="Review the 16-answer execution scope", owner_user_id="maya"),
                    AgendaItem(id="pricing-boundary", title="Confirm enterprise exception routing", owner_user_id="priya"),
                    AgendaItem(id="pricing-approval", title="Approve transition from Pre-work to Real work", owner_user_id="priya"),
                ],
                preparation_eligibility="eligible",
                preparation_reason="Pre-work approval meeting with a complete scope, evidence map, and authority boundary.",
                workroom_channel="agent-workroom-pricing-launch-faq",
                etag="demo-pricing-v1",
                updated_at=now,
            ),
            Meeting(
                id="meeting-welcome-coffee",
                calendar_event_id="demo-welcome-coffee",
                title="Welcome coffee with the team",
                description="Informal introductions for a new teammate.",
                start_at=welcome_start,
                end_at=welcome_start + timedelta(minutes=30),
                organizer_user_id="maya",
                attendee_user_ids=["shivam", "maya", "priya"],
                attendees=[attendees[0], attendees[1], attendees[4]],
                agenda=[],
                preparation_eligibility="skipped",
                preparation_reason="Social and introductory meetings are intentionally left human.",
                preparation_status="skipped",
                etag="demo-social-v1",
                updated_at=now,
            ),
            Meeting(
                id="meeting-northstar-onboarding-readiness",
                calendar_event_id="demo-northstar-onboarding-readiness",
                title="Northstar onboarding readiness",
                description="Review the agent-built onboarding pack, customer timeline, retention acknowledgment, and rollback ownership.",
                start_at=onboarding_start,
                end_at=onboarding_start + timedelta(minutes=45),
                organizer_user_id="maya",
                attendee_user_ids=["shivam", "maya", "alex", "priya"],
                attendees=[attendees[0], attendees[1], attendees[5], attendees[4]],
                agenda=[
                    AgendaItem(id="onboarding-pack", title="Review the 11 completed readiness checks", owner_user_id="maya"),
                    AgendaItem(id="onboarding-retention", title="Confirm retention-addendum acknowledgment", owner_user_id="alex"),
                    AgendaItem(id="onboarding-date", title="Resolve the executive progress-view date", owner_user_id="maya"),
                    AgendaItem(id="onboarding-rollback", title="Confirm controlled-enablement rollback owner", owner_user_id="shivam"),
                ],
                preparation_eligibility="eligible",
                preparation_reason="Customer onboarding review with completed multi-agent preparation and one timeline judgment.",
                workroom_channel="agent-workroom-northstar-onboarding",
                etag="demo-onboarding-v1",
                updated_at=now,
            ),
            Meeting(
                id="meeting-mobile-release-notes-review",
                calendar_event_id="demo-mobile-release-notes-review",
                title="Mobile 5.2 release notes review",
                description="Inspect the completed evidence manifest, privacy check, and Support handoff for the mobile release.",
                start_at=mobile_release_start,
                end_at=mobile_release_start + timedelta(minutes=30),
                organizer_user_id="daniel",
                attendee_user_ids=["shivam", "maya", "daniel", "priya"],
                attendees=[attendees[0], attendees[1], attendees[2], attendees[4]],
                agenda=[
                    AgendaItem(id="release-claims", title="Verify nine public claims against shipped changes", owner_user_id="daniel"),
                    AgendaItem(id="release-privacy", title="Confirm internal implementation details are excluded", owner_user_id="maya"),
                    AgendaItem(id="release-handoff", title="Accept the Support rollout handoff", owner_user_id="maya"),
                ],
                preparation_eligibility="eligible",
                preparation_reason="Completed agent project whose final evidence can replace a status-heavy review.",
                workroom_channel="agent-workroom-mobile-release-notes",
                etag="demo-mobile-notes-v1",
                updated_at=now,
            ),
            Meeting(
                id="meeting-agent-operations-review",
                calendar_event_id="demo-agent-operations-review",
                title="Weekly agent operations review",
                description="Review attention saved, denied requests, quarantined evidence, and the small set of work still requiring humans.",
                start_at=operating_review_start,
                end_at=operating_review_start + timedelta(minutes=30),
                organizer_user_id="shivam",
                attendee_user_ids=["shivam", "maya", "sarah", "alex", "priya"],
                attendees=[attendees[0], attendees[1], attendees[3], attendees[5], attendees[4]],
                agenda=[
                    AgendaItem(id="ops-attention", title="Review routine work resolved without interruption", owner_user_id="maya"),
                    AgendaItem(id="ops-safety", title="Review authorization denials and quarantined evidence", owner_user_id="sarah"),
                    AgendaItem(id="ops-review", title="Inspect projects currently paused for human review", owner_user_id="priya"),
                ],
                preparation_eligibility="eligible",
                preparation_reason="Operating review grounded in persisted mission, policy, and attention metrics.",
                workroom_channel="agent-workroom-atlas",
                etag="demo-agent-ops-v1",
                updated_at=now,
            ),
        ]

    def list_for_user(self, user_id: str) -> list[Meeting]:
        return sorted(
            [
                meeting for meeting in self.workspace.meetings.values()
                if user_id in meeting.attendee_user_ids
                or user_id == meeting.organizer_user_id
                or self._is_business_checkpoint_actor(meeting, user_id)
            ],
            key=lambda meeting: meeting.start_at,
        )

    def get_for_user(self, meeting_id: str, user_id: str) -> Meeting | None:
        meeting = self.workspace.meetings.get(meeting_id)
        if not meeting or (
            user_id not in meeting.attendee_user_ids
            and user_id != meeting.organizer_user_id
            and not self._is_business_checkpoint_actor(meeting, user_id)
        ):
            return None
        return meeting

    def _is_business_checkpoint_actor(self, meeting: Meeting, user_id: str) -> bool:
        run = self.workspace.meeting_runs.get(meeting.prep_run_id or "")
        mission = self.workspace.missions.get(run.mission_id or "") if run else None
        checkpoint = self.workspace.human_checkpoints.get(mission.business_checkpoint_id or "") if mission else None
        return bool(checkpoint and user_id in checkpoint.authorized_actor_ids)

    def upsert_from_calendar_event(self, event: WorkEvent) -> Meeting | None:
        """Project a privacy-minimized Calendar event into preparation state."""
        payload = event.payload
        calendar_event_id = str(payload.get("calendar_event_id", "")).strip()
        if not calendar_event_id:
            return None
        meeting_id = f"meeting-google-{sha256(calendar_event_id.encode()).hexdigest()[:16]}"
        existing = self.workspace.meetings.get(meeting_id)
        if event.event_type == "calendar.meeting.cancelled":
            if existing:
                existing.confirmed_action = "cancelled"
                existing.updated_at = event.occurred_at
                self.workspace.save_meeting(existing)
            return existing
        attendees: list[MeetingAttendee] = []
        attendee_ids: list[str] = []
        for item in payload.get("attendees", []):
            user_id = str(item.get("user_id", "")).strip()
            person = self.workspace.users.get(user_id)
            if not user_id or not person:
                continue
            response = str(item.get("response_status", "accepted")).replace("needsAction", "needs_action")
            if response not in {"accepted", "tentative", "declined", "needs_action"}:
                response = "accepted"
            attendees.append(MeetingAttendee(user_id=user_id, name=person.name, role=person.title, response_status=response))
            attendee_ids.append(user_id)
        organizer_id = str(payload.get("organizer_user_id", event.actor_user_id))
        if organizer_id not in attendee_ids and organizer_id in self.workspace.users:
            organizer = self.workspace.users[organizer_id]
            attendees.insert(0, MeetingAttendee(user_id=organizer_id, name=organizer.name, role=organizer.title))
            attendee_ids.insert(0, organizer_id)
        description = str(payload.get("description", "")).strip()
        agenda_titles = [line.strip(" -*\t") for line in description.splitlines() if line.strip(" -*\t")][:6]
        if not agenda_titles:
            agenda_titles = ["Review current status and unresolved decisions"]
        meeting_title = str(payload.get("title", "Untitled work meeting"))
        is_atlas = "atlas" in f"{meeting_title} {description}".lower()
        new_etag = str(payload.get("etag", "")) or sha256(event.id.encode()).hexdigest()[:16]
        status = "stale" if existing and existing.prep_run_id and existing.etag != new_etag else (existing.preparation_status if existing else "not_started")
        meeting = Meeting(
            id=meeting_id,
            calendar_event_id=calendar_event_id,
            title=meeting_title,
            description=description,
            start_at=datetime.fromisoformat(str(payload["start_at"]).replace("Z", "+00:00")),
            end_at=datetime.fromisoformat(str(payload["end_at"]).replace("Z", "+00:00")),
            organizer_user_id=organizer_id,
            attendee_user_ids=attendee_ids,
            attendees=attendees,
            agenda=[
                AgendaItem(
                    id=f"calendar-agenda-{index}",
                    title=title,
                    authority_type=(
                        "atlas_security_approval"
                        if is_atlas and "security" in title.lower() and any(term in title.lower() for term in ("decision", "exception", "approval"))
                        else None
                    ),
                )
                for index, title in enumerate(agenda_titles, 1)
            ],
            preparation_eligibility=str(payload.get("preparation_eligibility", "ambiguous")),
            preparation_reason=str(payload.get("preparation_reason", "Calendar work meeting.")),
            preparation_status=status,
            prep_run_id=existing.prep_run_id if existing else None,
            workroom_channel=existing.workroom_channel if existing else None,
            etag=new_etag,
            updated_at=event.occurred_at,
            source="google_calendar",
            conference_uri=str(payload.get("conference_uri", "")).strip() or None,
            conference_code=str(payload.get("conference_code", "")).strip() or None,
            confirmed_action=existing.confirmed_action if existing else "none",
            pending_action=existing.pending_action if existing else "none",
            approved_recommendation=existing.approved_recommendation if existing else "none",
            attendance_plans=existing.attendance_plans if existing else {},
        )
        self.workspace.save_meeting(meeting)
        return meeting

    def prepare(self, meeting: Meeting, actor_id: str, trigger: str = "manual") -> MeetingPrepRun:
        if meeting.preparation_eligibility == "skipped":
            raise ValueError("This meeting is intentionally excluded from agent preparation")
        if self.mission_runtime is None:
            raise RuntimeError("Meeting mission runtime is not configured")
        if meeting.prep_run_id:
            existing = self.workspace.meeting_runs.get(meeting.prep_run_id)
            existing_mission = self.workspace.missions.get(existing.mission_id or "") if existing else None
            if (
                existing
                and existing.status == "completed"
                and existing_mission
                and existing_mission.workflow_version == self.mission_runtime.WORKFLOW_VERSION
                and meeting.preparation_status != "stale"
            ):
                return existing

        now = self.now_fn()
        mission = self.mission_runtime.start(meeting, actor_id, trigger)
        run = self.mission_runtime.project_meeting_run(mission, meeting)
        meeting.preparation_status = "completed"
        meeting.prep_run_id = run.id
        meeting.updated_at = now
        self.workspace.save_meeting_run(run)
        self.workspace.save_meeting(meeting)
        self.workspace.increment_stat("meetings_prepared")
        self.workspace.increment_stat("meeting_minutes_saved", run.brief.minutes_saved if run.brief else 0)
        self.workspace.append_audit(AuditEvent(
            event_type="meeting.prepared",
            actor_id=actor_id,
            entity_ids=[meeting.id, run.id, mission.id],
            summary=f"{meeting.title} prepared from a durable mission; {run.brief.minutes_saved if run.brief else 0} minutes can be returned.",
            created_at=now,
            metadata={
                "trigger": trigger,
                "disposition": run.brief.recommended_disposition if run.brief else "keep",
                "trace_id": mission.trace_id,
            },
        ))
        return run

    def confirm_action(self, meeting: Meeting, request: MeetingActionRequest) -> Meeting:
        if request.actor_id != meeting.organizer_user_id:
            raise PermissionError("Only the meeting organizer can approve Calendar changes")
        if request.expected_etag != meeting.etag:
            meeting.preparation_status = "stale"
            self.workspace.save_meeting(meeting)
            raise RuntimeError("The Calendar event changed after preparation; rerun before approving an action")
        run = self.workspace.meeting_runs.get(meeting.prep_run_id or "")
        if not run or not run.brief or not run.mission_id:
            raise ValueError("Prepare the meeting with a durable mission before approving an action")
        if request.action != run.brief.recommended_disposition and not (
            request.action == "update_agenda" and run.brief.recommended_disposition == "shorten"
        ):
            raise ValueError("The requested action does not match the mission recommendation")
        mission = self.workspace.missions[run.mission_id]
        if mission.business_checkpoint_id:
            business_checkpoint = self.workspace.human_checkpoints[mission.business_checkpoint_id]
            if business_checkpoint.status != "approved":
                raise ValueError("The authorized business decision must be approved before Calendar consent")
        if not mission.calendar_checkpoint_id:
            raise ValueError("This mission has not reached the Calendar action gate")
        checkpoint = self.workspace.human_checkpoints[mission.calendar_checkpoint_id]
        resolved_mission = self.mission_runtime.resolve_checkpoint(
            checkpoint.id,
            MissionCheckpointResolution(
                actor_id=request.actor_id,
                decision="approved",
                rationale=f"Organizer approved the mission recommendation to {request.action}.",
            ),
            meeting,
        )
        if resolved_mission.proposed_commands:
            meeting.pending_action = request.action
        else:
            meeting.approved_recommendation = request.action
        meeting.updated_at = self.now_fn()
        self.workspace.save_meeting(meeting)
        self.workspace.append_audit(AuditEvent(
            event_type="meeting.calendar_action_queued" if resolved_mission.proposed_commands else "meeting.recommendation_approved",
            actor_id=request.actor_id,
            entity_ids=[meeting.id, mission.id, checkpoint.id],
            summary=(
                f"Organizer approved {request.action} for {meeting.title}; execution was queued to the isolated action service."
                if resolved_mission.proposed_commands
                else f"Organizer approved the {request.action} recommendation for {meeting.title}; demo data was not mutated."
            ),
            created_at=meeting.updated_at,
            metadata={"action": request.action, "expected_etag": meeting.etag},
        ))
        return meeting
