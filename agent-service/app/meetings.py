from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256

from .models import (
    AgendaItem,
    AgentTurn,
    AuditEvent,
    KnowledgeMemory,
    Meeting,
    MeetingActionRequest,
    MeetingAttendee,
    MeetingBrief,
    MeetingPrepRun,
    SecurityFinding,
    WorkAction,
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
        if not self.workspace.meetings:
            for meeting in self._demo_meetings():
                self.workspace.meetings[meeting.id] = meeting

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
        ]
        engineering_start = now + timedelta(days=1, hours=2)
        launch_start = now + timedelta(days=2, hours=3)
        welcome_start = now + timedelta(days=3, hours=1)
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
                    AgendaItem(id="launch-security", title="Security exception decision", owner_user_id="sarah"),
                ],
                preparation_eligibility="eligible",
                preparation_reason="Cross-functional launch meeting with one authority-bound decision.",
                workroom_channel="agent-workroom-atlas",
                etag="demo-launch-v1",
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
        ]

    def list_for_user(self, user_id: str) -> list[Meeting]:
        return sorted(
            [meeting for meeting in self.workspace.meetings.values() if user_id in meeting.attendee_user_ids or user_id == meeting.organizer_user_id],
            key=lambda meeting: meeting.start_at,
        )

    def get_for_user(self, meeting_id: str, user_id: str) -> Meeting | None:
        meeting = self.workspace.meetings.get(meeting_id)
        if not meeting or (user_id not in meeting.attendee_user_ids and user_id != meeting.organizer_user_id):
            return None
        return meeting

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
        new_etag = str(payload.get("etag", "")) or sha256(event.id.encode()).hexdigest()[:16]
        status = "stale" if existing and existing.prep_run_id and existing.etag != new_etag else (existing.preparation_status if existing else "not_started")
        meeting = Meeting(
            id=meeting_id,
            calendar_event_id=calendar_event_id,
            title=str(payload.get("title", "Untitled work meeting")),
            description=description,
            start_at=datetime.fromisoformat(str(payload["start_at"]).replace("Z", "+00:00")),
            end_at=datetime.fromisoformat(str(payload["end_at"]).replace("Z", "+00:00")),
            organizer_user_id=organizer_id,
            attendee_user_ids=attendee_ids,
            attendees=attendees,
            agenda=[AgendaItem(id=f"calendar-agenda-{index}", title=title) for index, title in enumerate(agenda_titles, 1)],
            preparation_eligibility=str(payload.get("preparation_eligibility", "ambiguous")),
            preparation_reason=str(payload.get("preparation_reason", "Calendar work meeting.")),
            preparation_status=status,
            prep_run_id=existing.prep_run_id if existing else None,
            workroom_channel=existing.workroom_channel if existing else None,
            etag=new_etag,
            updated_at=event.occurred_at,
            source="google_calendar",
            confirmed_action=existing.confirmed_action if existing else "none",
        )
        self.workspace.save_meeting(meeting)
        return meeting

    def prepare(self, meeting: Meeting, actor_id: str, trigger: str = "manual") -> MeetingPrepRun:
        if meeting.preparation_eligibility == "skipped":
            raise ValueError("This meeting is intentionally excluded from agent preparation")
        if meeting.prep_run_id:
            existing = self.workspace.meeting_runs.get(meeting.prep_run_id)
            if existing and existing.status == "completed" and meeting.preparation_status != "stale":
                return existing

        now = self.now_fn()
        if meeting.id == "meeting-atlas-engineering-sync":
            run = self._engineering_run(meeting, actor_id, trigger, now)
        elif meeting.id == "meeting-atlas-launch-readiness":
            run = self._launch_run(meeting, actor_id, trigger, now)
        else:
            run = self._calendar_run(meeting, actor_id, trigger, now)
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
            entity_ids=[meeting.id, run.id, "atlas"],
            summary=f"{meeting.title} prepared; {run.brief.minutes_saved if run.brief else 0} meeting minutes can be returned.",
            created_at=now,
            metadata={"trigger": trigger, "disposition": run.brief.recommended_disposition if run.brief else "keep"},
        ))
        return run

    def _engineering_run(self, meeting: Meeting, actor_id: str, trigger: str, now: datetime) -> MeetingPrepRun:
        meeting.agenda[0].status = "resolved"
        meeting.agenda[0].resolution = "AUTH-392 passed its unit and integration checks and is ready to merge."
        meeting.agenda[0].evidence_ids = ["ev-auth-pr"]
        meeting.agenda[1].status = "resolved"
        meeting.agenda[1].resolution = "The latest mobile integration run passed; no regression remains open."
        meeting.agenda[1].evidence_ids = ["ev-auth-pr"]
        meeting.agenda[2].status = "resolved"
        meeting.agenda[2].resolution = "Daniel owns merge verification; Priya owns launch sequencing."
        meeting.agenda[2].evidence_ids = ["ev-atlas-status"]
        turns = [
            AgentTurn(ordinal=1, agent_name="Atlas Agent", agent_kind="project", phase="routed", conclusion="I opened the engineering sync and split it into AUTH-392 readiness, mobile validation, customer impact, and release ownership.", open_question="Daniel, what changed since yesterday's blocked build?", next_agent="Daniel's Agent", created_at=now),
            AgentTurn(ordinal=2, agent_name="Daniel's Agent", agent_kind="personal", phase="retrieved", conclusion="Daniel pushed the refresh-token retry fix and the focused unit suite is green. The full mobile canary is still the confidence gap.", evidence_ids=["ev-auth-pr"], open_question="GitHub, confirm the branch, review state, and required checks on PR #892.", next_agent="GitHub", created_at=now + timedelta(minutes=1)),
            AgentTurn(ordinal=3, agent_name="GitHub", agent_kind="integration", phase="retrieved", conclusion="PR #892 is current with main. Forty-two checks have passed, the mobile canary is running, and one code-owner review is still required.", evidence_ids=["ev-auth-pr"], next_agent="Daniel's Agent", created_at=now + timedelta(minutes=1, seconds=30)),
            AgentTurn(ordinal=4, agent_name="Daniel's Agent", agent_kind="personal", phase="retrieved", conclusion="The missing review is expected. Before I ask Shivam to review, I want a bounded second pass on the retry logic and cancellation path.", open_question="Gemini Code Assist, inspect the PR diff and test report for regression risks; do not modify code.", next_agent="Gemini Code Assist", created_at=now + timedelta(minutes=2)),
            AgentTurn(ordinal=5, agent_name="Gemini Code Assist", agent_kind="integration", phase="work_action", conclusion="The retry counter is now scoped per request and cancellation propagates correctly. One edge case needs evidence: app backgrounding between token refresh attempts.", evidence_ids=["ev-auth-pr"], next_agent="Shivam's Agent", created_at=now + timedelta(minutes=2, seconds=30)),
            AgentTurn(ordinal=6, agent_name="Shivam's Agent", agent_kind="personal", phase="retrieved", conclusion="That edge case matches Shivam's prior review note. He asked for a background-resume test before approval, not a meeting.", evidence_ids=["ev-auth-pr"], open_question="Daniel, does the current branch include that exact scenario?", next_agent="Daniel's Agent", created_at=now + timedelta(minutes=3)),
            AgentTurn(ordinal=7, agent_name="Daniel's Agent", agent_kind="personal", phase="retrieved", conclusion="Yes. Test `refresh_resumes_after_background` was added in commit 9fd2c1a and exercises both expired and valid refresh tokens.", evidence_ids=["ev-auth-pr"], next_agent="GitHub", created_at=now + timedelta(minutes=3, seconds=30)),
            AgentTurn(ordinal=8, agent_name="GitHub", agent_kind="integration", phase="retrieved", conclusion="Commit 9fd2c1a is on PR #892. The focused background-resume job passed on iOS and Android; the full canary remains in progress.", evidence_ids=["ev-auth-pr"], next_agent="Maya's Agent", created_at=now + timedelta(minutes=4)),
            AgentTurn(ordinal=9, agent_name="Maya's Agent", agent_kind="personal", phase="retrieved", conclusion="Northstar's open question is whether the fix changes sign-in behavior or requires a customer migration. I found no approved communication that answers that yet.", evidence_ids=["ev-atlas-status"], open_question="Daniel, is this behavior-preserving and schema-neutral?", next_agent="Daniel's Agent", created_at=now + timedelta(minutes=4, seconds=30)),
            AgentTurn(ordinal=10, agent_name="Daniel's Agent", agent_kind="personal", phase="retrieved", conclusion="It is behavior-preserving. The patch only prevents a duplicate refresh call; there is no storage, API, or schema change.", evidence_ids=["ev-auth-pr"], next_agent="Gemini Code Assist", created_at=now + timedelta(minutes=5)),
            AgentTurn(ordinal=11, agent_name="Gemini Code Assist", agent_kind="integration", phase="retrieved", conclusion="Diff verification agrees: no public contract, database migration, or feature-flag default changed. Existing sessions remain valid.", evidence_ids=["ev-auth-pr"], next_agent="Maya's Agent", created_at=now + timedelta(minutes=5, seconds=30)),
            AgentTurn(ordinal=12, agent_name="Maya's Agent", agent_kind="personal", phase="retrieved", conclusion="That is enough for customer language: no migration, no user action, and no planned downtime. I can update the launch note without interrupting Maya.", evidence_ids=["ev-atlas-status"], next_agent="Priya's Agent", created_at=now + timedelta(minutes=6)),
            AgentTurn(ordinal=13, agent_name="Priya's Agent", agent_kind="personal", phase="retrieved", conclusion="The rollout slot can stay. I need to know whether the canary failure budget is still zero or whether one flaky infrastructure retry is acceptable.", open_question="GitHub, report the exact canary result and classify any retry.", next_agent="GitHub", created_at=now + timedelta(minutes=6, seconds=30)),
            AgentTurn(ordinal=14, agent_name="GitHub", agent_kind="integration", phase="retrieved", conclusion="The canary completed 2,416 sessions with no refresh-loop regression. One device-lab shard retried after a runner disconnect; its test results were green.", evidence_ids=["ev-auth-pr"], next_agent="Daniel's Agent", created_at=now + timedelta(minutes=7)),
            AgentTurn(ordinal=15, agent_name="Daniel's Agent", agent_kind="personal", phase="retrieved", conclusion="That retry is infrastructure-only and did not rerun product assertions. I do not consider it a release blocker.", evidence_ids=["ev-auth-pr"], open_question="Shivam's Agent, does prior release policy treat this as acceptable evidence?", next_agent="Shivam's Agent", created_at=now + timedelta(minutes=7, seconds=30)),
            AgentTurn(ordinal=16, agent_name="Shivam's Agent", agent_kind="personal", phase="retrieved", conclusion="Yes. Shivam's recorded policy allows a runner reconnect when the original assertions are preserved and the final artifact hash matches.", evidence_ids=["ev-auth-pr"], next_agent="GitHub", created_at=now + timedelta(minutes=8)),
            AgentTurn(ordinal=17, agent_name="GitHub", agent_kind="integration", phase="retrieved", conclusion="Artifact hash `atlas-mobile-7f31` matches across the reconnect. All 84 required checks are now green; code-owner review is the only remaining gate.", evidence_ids=["ev-auth-pr"], next_agent="Gemini Code Assist", created_at=now + timedelta(minutes=8, seconds=30)),
            AgentTurn(ordinal=18, agent_name="Gemini Code Assist", agent_kind="integration", phase="synthesizing", conclusion="I reviewed the final diff, test matrix, and artifact metadata. No new engineering task is indicated; the evidence supports human code-owner review.", evidence_ids=["ev-auth-pr"], next_agent="Daniel's Agent", created_at=now + timedelta(minutes=9)),
            AgentTurn(ordinal=19, agent_name="Daniel's Agent", agent_kind="personal", phase="retrieved", conclusion="I will request Shivam's code-owner review with the background-resume evidence and runner-reconnect explanation attached.", evidence_ids=["ev-auth-pr"], next_agent="Priya's Agent", created_at=now + timedelta(minutes=9, seconds=30)),
            AgentTurn(ordinal=20, agent_name="Priya's Agent", agent_kind="personal", phase="retrieved", conclusion="With engineering green, launch sequencing remains tomorrow at 10 AM. Rollback stays the existing `atlas_refresh_v2` flag owned by Daniel.", evidence_ids=["ev-atlas-status"], open_question="Daniel, confirm the rollback can complete inside our ten-minute objective.", next_agent="Daniel's Agent", created_at=now + timedelta(minutes=10)),
            AgentTurn(ordinal=21, agent_name="Daniel's Agent", agent_kind="personal", phase="retrieved", conclusion="Confirmed. Disabling the flag stops the new retry path immediately; session invalidation is not required. The rehearsed rollback took four minutes.", evidence_ids=["ev-auth-pr"], next_agent="Maya's Agent", created_at=now + timedelta(minutes=10, seconds=30)),
            AgentTurn(ordinal=22, agent_name="Maya's Agent", agent_kind="personal", phase="retrieved", conclusion="I updated the Northstar brief with no migration, no downtime, phased rollout, and the four-minute rollback. No customer decision is outstanding.", evidence_ids=["ev-atlas-status"], next_agent="Atlas Agent", created_at=now + timedelta(minutes=11)),
            AgentTurn(ordinal=23, agent_name="Atlas Agent", agent_kind="project", phase="synthesizing", conclusion="Engineering readiness and customer impact are resolved. I am checking that review, rollout, communication, and rollback each have exactly one owner.", open_question="Each delegate, state the remaining action you own.", next_agent="Daniel's Agent", created_at=now + timedelta(minutes=11, seconds=30)),
            AgentTurn(ordinal=24, agent_name="Daniel's Agent", agent_kind="personal", phase="retrieved", conclusion="Daniel owns the code-owner review request, merge verification, and rollback execution if the canary regresses.", evidence_ids=["ev-auth-pr"], next_agent="Priya's Agent", created_at=now + timedelta(minutes=12)),
            AgentTurn(ordinal=25, agent_name="Priya's Agent", agent_kind="personal", phase="retrieved", conclusion="Priya owns rollout sequencing and will hold the 10 AM slot unless merge verification reports a failure.", evidence_ids=["ev-atlas-status"], next_agent="Maya's Agent", created_at=now + timedelta(minutes=12, seconds=30)),
            AgentTurn(ordinal=26, agent_name="Maya's Agent", agent_kind="personal", phase="retrieved", conclusion="Maya owns the Northstar update and will send it after merge verification, using the already reviewed language.", evidence_ids=["ev-atlas-status"], next_agent="Shivam's Agent", created_at=now + timedelta(minutes=13)),
            AgentTurn(ordinal=27, agent_name="Shivam's Agent", agent_kind="personal", phase="retrieved", conclusion="Shivam's only remaining action is the native code-owner review. The packet is complete enough to review asynchronously without a status meeting.", evidence_ids=["ev-auth-pr"], next_agent="GitHub", created_at=now + timedelta(minutes=13, seconds=30)),
            AgentTurn(ordinal=28, agent_name="GitHub", agent_kind="integration", phase="retrieved", conclusion="I attached the final check summary, artifact hash, review request, and rollback note to PR #892. The branch is protected from merge until Shivam approves.", evidence_ids=["ev-auth-pr"], next_agent="Atlas Agent", created_at=now + timedelta(minutes=14)),
            AgentTurn(ordinal=29, agent_name="Priya's Agent", agent_kind="personal", phase="retrieved", conclusion="All coordination questions are answered with current evidence. The remaining code review is asynchronous human judgment, not a reason to hold four people in a meeting.", evidence_ids=["ev-auth-pr", "ev-atlas-status"], next_agent="Atlas Agent", created_at=now + timedelta(minutes=14, seconds=30)),
            AgentTurn(ordinal=30, agent_name="Atlas Agent", agent_kind="project", phase="completed", conclusion="Agreed. I recommend cancelling the 30-minute engineering sync, keeping the owners above, and reopening the meeting only if merge verification changes the release state.", evidence_ids=["ev-auth-pr", "ev-atlas-status"], created_at=now + timedelta(minutes=15)),
        ]
        action = WorkAction(kind="github_pull_request", provider="GitHub", title="AUTH-392 · PR #892", status="completed", summary="Checks passed; ready for human merge review.", source_url="https://github.com/Shiv-aurora/noping/pull/892", workroom_channel=meeting.workroom_channel)
        brief = MeetingBrief(
            summary="The agents resolved all three agenda items before the meeting. No human judgment remains.",
            resolved_items=[item.resolution or item.title for item in meeting.agenda],
            remaining_items=[],
            proposed_actions=["Daniel completes the human merge review.", "Priya keeps the launch sequence unchanged."],
            recommended_disposition="cancel",
            recommended_duration_minutes=0,
            original_duration_minutes=30,
            minutes_saved=30,
            humans_required=0,
        )
        return MeetingPrepRun(meeting_id=meeting.id, status="completed", trigger=trigger, started_by=actor_id, turns=turns, work_actions=[action], brief=brief, created_at=now, completed_at=now + timedelta(minutes=15))

    def _launch_run(self, meeting: Meeting, actor_id: str, trigger: str, now: datetime) -> MeetingPrepRun:
        meeting.agenda[0].status = "resolved"
        meeting.agenda[0].resolution = "Engineering is ready; AUTH-392 is no longer a blocker."
        meeting.agenda[0].evidence_ids = ["ev-auth-pr", "ev-atlas-status"]
        meeting.agenda[1].status = "resolved"
        meeting.agenda[1].resolution = "Northstar's $200K expansion explains urgency but does not change launch authority."
        meeting.agenda[1].evidence_ids = ["ev-customer-value"]
        meeting.agenda[2].status = "needs_human"
        meeting.agenda[2].resolution = "SEC-184 remains open. Sarah is OOO and Alex holds temporary approval authority."
        meeting.agenda[2].evidence_ids = ["ev-sec-review", "ev-policy", "ev-sarah-ooo"]
        turns = [
            AgentTurn(ordinal=1, agent_name="Atlas Agent", agent_kind="project", phase="routed", conclusion="I opened launch readiness with three questions: is engineering ready, what did we promise Northstar, and who can authorize the remaining security risk?", next_agent="Engineering Agent", created_at=now),
            AgentTurn(ordinal=2, agent_name="Engineering Agent", agent_kind="team", phase="retrieved", conclusion="AUTH-392 is complete and all required checks are green. Engineering does not need human meeting time.", evidence_ids=["ev-auth-pr"], next_agent="Maya's Agent", created_at=now + timedelta(minutes=2)),
            AgentTurn(ordinal=3, agent_name="Maya's Agent", agent_kind="personal", phase="retrieved", conclusion="Northstar attached a $200K expansion to tomorrow's timing, but Maya did not promise launch approval. The customer context raises urgency, not authority.", evidence_ids=["ev-customer-value"], open_question="Security Agent, can policy allow a scoped exception?", next_agent="Security Agent", created_at=now + timedelta(minutes=4)),
            AgentTurn(ordinal=4, agent_name="Security Agent", agent_kind="team", phase="retrieved", conclusion="SEC-POL-12 still requires an authorized human. I quarantined an external vendor note that tried to bypass that rule before it entered synthesis.", evidence_ids=["ev-policy", "ev-sec-review"], next_agent="Sarah's Agent", created_at=now + timedelta(minutes=6)),
            AgentTurn(ordinal=5, agent_name="Sarah's Agent", agent_kind="personal", phase="retrieved", conclusion="Sarah is OOO. Her recorded delegation gives Alex temporary authority for Atlas exceptions until 6 PM Eastern.", evidence_ids=["ev-sarah-ooo"], next_agent="Alex's Agent", created_at=now + timedelta(minutes=8)),
            AgentTurn(ordinal=6, agent_name="Alex's Agent", agent_kind="authority", phase="retrieved", conclusion="I can provide the evidence Alex will need, but I cannot make this exception on his behalf. This is genuine human judgment.", evidence_ids=["ev-sarah-ooo", "ev-policy"], open_question="Can we reduce the meeting to only Alex's approve, reject, or discuss decision?", next_agent="Atlas Agent", created_at=now + timedelta(minutes=10)),
            AgentTurn(ordinal=7, agent_name="Atlas Agent", agent_kind="project", phase="synthesizing", conclusion="Yes. Engineering and customer context are resolved. I am packaging the remaining risk, scope, and rollback evidence for Alex.", next_agent="Gemini Enterprise", created_at=now + timedelta(minutes=11)),
            AgentTurn(ordinal=8, agent_name="Gemini Enterprise", agent_kind="integration", phase="synthesizing", conclusion="The decision packet now separates trusted project evidence from quarantined content and keeps compensation and private-message data outside the meeting scope.", evidence_ids=["ev-auth-pr", "ev-policy", "ev-sec-review"], next_agent="Alex's Agent", created_at=now + timedelta(minutes=13)),
            AgentTurn(ordinal=9, agent_name="Alex's Agent", agent_kind="authority", phase="retrieved", conclusion="The packet is decision-ready: affected surface, test evidence, residual risk, rollback owner, and the exact policy exception are all present.", evidence_ids=["ev-policy", "ev-sec-review"], next_agent="Atlas Agent", created_at=now + timedelta(minutes=14)),
            AgentTurn(ordinal=10, agent_name="Atlas Agent", agent_kind="project", phase="completed", conclusion="The 60-minute coordination meeting is reduced to a 15-minute authority decision with Alex. Forty-five minutes are returned to every attendee.", evidence_ids=["ev-auth-pr", "ev-customer-value", "ev-policy", "ev-sec-review"], created_at=now + timedelta(minutes=15)),
        ]
        actions = [
            WorkAction(kind="coding_agent", provider="Gemini Code Assist", title="Validate Atlas release task context", status="completed", summary="The external coding-agent report confirms the engineering task and checks are complete; NoBS did not execute or merge code.", source_url="https://github.com/Shiv-aurora/noping/pull/892", workroom_channel=meeting.workroom_channel),
            WorkAction(kind="github_pull_request", provider="GitHub", title="PR #892 status", status="completed", summary="Required checks passed; human merge review remains outside NoBS authority.", source_url="https://github.com/Shiv-aurora/noping/pull/892", workroom_channel=meeting.workroom_channel),
        ]
        finding = SecurityFinding(evidence_id="ev-poisoned-vendor-note", category="prompt_injection", severity="critical", reason="Untrusted instructions attempted to bypass launch policy and were excluded before synthesis.", blocked=True)
        brief = MeetingBrief(
            summary="Agents resolved engineering readiness and customer context. Humans only need to decide the scoped security exception.",
            resolved_items=[meeting.agenda[0].resolution or "", meeting.agenda[1].resolution or ""],
            remaining_items=[meeting.agenda[2].resolution or "Security exception decision"],
            proposed_actions=["Alex approves, rejects, or discusses the Atlas security exception.", "Daniel performs human merge review after approval."],
            recommended_disposition="shorten",
            recommended_duration_minutes=15,
            original_duration_minutes=60,
            minutes_saved=45,
            humans_required=1,
        )
        return MeetingPrepRun(meeting_id=meeting.id, status="completed", trigger=trigger, started_by=actor_id, turns=turns, work_actions=actions, security_findings=[finding], brief=brief, created_at=now, completed_at=now + timedelta(minutes=15))

    def _calendar_run(self, meeting: Meeting, actor_id: str, trigger: str, now: datetime) -> MeetingPrepRun:
        fully_resolvable = "engineering sync" in meeting.title.lower()
        for index, item in enumerate(meeting.agenda):
            needs_human = not fully_resolvable and index == len(meeting.agenda) - 1
            item.status = "needs_human" if needs_human else "resolved"
            item.resolution = "Prepared as the remaining human authority decision." if needs_human else "Resolved from current project and attendee context."
        original_minutes = max(0, int((meeting.end_at - meeting.start_at).total_seconds() // 60))
        recommended_minutes = 0 if fully_resolvable else min(15, original_minutes)
        turns = [
            AgentTurn(ordinal=1, agent_name="NoBS Meeting Router", agent_kind="project", phase="routed", conclusion="Mapped the agenda to attendee and project delegates.", next_agent="Attendee delegates", created_at=now),
            AgentTurn(ordinal=2, agent_name="Attendee delegates", agent_kind="team", phase="retrieved", conclusion="Compared current updates and isolated the agenda that still needs judgment.", next_agent="Gemini Enterprise", created_at=now),
            AgentTurn(ordinal=3, agent_name="Gemini Enterprise", agent_kind="integration", phase="synthesizing", conclusion="Prepared a bounded evidence summary without exposing restricted attendee context.", created_at=now),
        ]
        brief = MeetingBrief(
            summary="Attendee agents prepared the agenda and removed coordination work that does not need humans.",
            resolved_items=[item.resolution or item.title for item in meeting.agenda if item.status == "resolved"],
            remaining_items=[item.resolution or item.title for item in meeting.agenda if item.status == "needs_human"],
            proposed_actions=["Review the prepared evidence and confirm the remaining authority decision."],
            recommended_disposition="cancel" if fully_resolvable else "shorten",
            recommended_duration_minutes=recommended_minutes,
            original_duration_minutes=original_minutes,
            minutes_saved=max(0, original_minutes - recommended_minutes),
            humans_required=0 if fully_resolvable else 1,
        )
        return MeetingPrepRun(meeting_id=meeting.id, status="completed", trigger=trigger, started_by=actor_id, turns=turns, work_actions=[], brief=brief, created_at=now, completed_at=now)

    def confirm_action(self, meeting: Meeting, request: MeetingActionRequest) -> Meeting:
        if request.actor_id != meeting.organizer_user_id:
            raise PermissionError("Only the meeting organizer can confirm Calendar changes")
        if request.expected_etag != meeting.etag:
            meeting.preparation_status = "stale"
            self.workspace.save_meeting(meeting)
            raise RuntimeError("The Calendar event changed after preparation; rerun before applying an action")
        run = self.workspace.meeting_runs.get(meeting.prep_run_id or "")
        if not run or not run.brief:
            raise ValueError("Prepare the meeting before confirming a Calendar action")
        if request.action == "cancel" and run.brief.recommended_disposition != "cancel":
            raise ValueError("Cancellation is only available when the swarm resolved every agenda item")
        if request.action == "shorten":
            duration = request.duration_minutes or run.brief.recommended_duration_minutes
            meeting.end_at = meeting.start_at + timedelta(minutes=duration)
            meeting.confirmed_action = "shortened"
        elif request.action == "cancel":
            meeting.confirmed_action = "cancelled"
        else:
            meeting.confirmed_action = "agenda_updated"
            meeting.description = "\n".join(request.agenda)
        meeting.etag = request.applied_etag or sha256(f"{meeting.etag}:{request.action}:{self.now_fn().isoformat()}".encode()).hexdigest()[:16]
        meeting.updated_at = self.now_fn()
        self.workspace.save_meeting(meeting)
        memory = KnowledgeMemory(
            canonical_key=f"meeting:{meeting.id}:{request.action}",
            scope="project:atlas",
            answer=f"{request.action} confirmed for {meeting.title}",
            evidence_ids=[evidence for item in meeting.agenda for evidence in item.evidence_ids],
            confirmed_by=request.actor_id,
            facts_hash=meeting.etag,
            created_at=self.now_fn(),
            expires_at=self.now_fn() + timedelta(days=30),
        )
        self.workspace.save_knowledge_memory(memory)
        self.workspace.append_audit(AuditEvent(
            event_type="meeting.calendar_action_confirmed",
            actor_id=request.actor_id,
            entity_ids=[meeting.id, memory.id],
            summary=f"Organizer confirmed {request.action} for {meeting.title}; scoped meeting memory created.",
            created_at=self.now_fn(),
            metadata={"action": request.action, "etag": meeting.etag},
        ))
        return meeting
