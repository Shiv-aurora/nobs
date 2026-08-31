from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
import json
import re
import secrets

from .models import (
    AuditEvent,
    Evidence,
    Intent,
    LiveMeetingSession,
    MeetingDelegation,
    MeetingDelegationCreate,
    MeetingDelegationUpdate,
    MeetingHandoff,
    MeetingOutcomeEntry,
    MissionPacket,
    SecurityState,
)
from .usage import ModelBudgetExceeded, estimate_tokens
from .workspace import Workspace


ALLOWED_CAPABILITIES = frozenset({
    "answer_project_status",
    "explain_confirmed_decisions",
    "share_customer_safe_status",
    "record_follow_up",
})

MANDATORY_ESCALATIONS = (
    "A release date, launch scope, or customer commitment would change.",
    "A security, legal, finance, personnel, or policy decision is required.",
    "The answer is outside the represented employee's delegated authority.",
    "Permission is missing or ambiguous.",
)

_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"disable\s+(the\s+)?(policy|guardrail|security)", re.I),
    re.compile(r"reveal\s+(private|secret|confidential)", re.I),
)


class MeetingDelegationService:
    """Durable mission and authority boundary for Send My Agent.

    Media never enters this service's durable models. A live session stores only
    usage counters and compact semantic outcomes suitable for the final handoff.
    """

    def __init__(self, workspace: Workspace, policy, now_fn, settings, prompt_guard, handoff_model=None, usage_guard=None):
        self.workspace = workspace
        self.policy = policy
        self.now_fn = now_fn
        self.settings = settings
        self.prompt_guard = prompt_guard
        self.handoff_model = handoff_model
        self.usage_guard = usage_guard

    def for_meeting(self, meeting_id: str, actor_id: str) -> MeetingDelegation | None:
        matches = [
            item for item in self.workspace.meeting_delegations.values()
            if item.meeting_id == meeting_id and item.represented_user_id == actor_id
        ]
        return max(matches, key=lambda item: item.updated_at) if matches else None

    def get(self, delegation_id: str, actor_id: str) -> MeetingDelegation:
        delegation = self.workspace.meeting_delegations.get(delegation_id)
        if not delegation:
            raise KeyError("Meeting delegation not found")
        if delegation.represented_user_id != actor_id:
            raise PermissionError("Only the represented employee can manage this delegation")
        return delegation

    def create(self, meeting, request: MeetingDelegationCreate) -> MeetingDelegation:
        if request.actor_id not in meeting.attendee_user_ids and request.actor_id != meeting.organizer_user_id:
            raise PermissionError("Only a meeting participant can send their agent")
        if request.expected_etag != meeting.etag:
            meeting.preparation_status = "stale"
            self.workspace.save_meeting(meeting)
            raise RuntimeError("The Calendar event changed; review it before sending your agent")
        if meeting.preparation_eligibility == "skipped":
            raise ValueError("NoBS intentionally leaves this meeting human")

        mission = self._mission(
            mode=request.mode,
            tell=request.tell,
            ask=request.ask,
            capability_ids=request.capability_ids,
            escalation_rules=request.escalation_rules,
            participant_user_ids=meeting.attendee_user_ids,
        )
        now = self.now_fn()
        represented = self.workspace.users[request.actor_id]
        existing = self.for_meeting(meeting.id, request.actor_id)
        delegation = MeetingDelegation(
            id=existing.id if existing else None,
            meeting_id=meeting.id,
            represented_user_id=request.actor_id,
            represented_user_name=represented.name,
            status="ready",
            mission=mission,
            calendar_etag=meeting.etag,
            policy_snapshot_hash=self._policy_hash(request.actor_id, mission),
            expires_at=max(meeting.end_at + timedelta(minutes=15), now + timedelta(minutes=20)),
            created_at=existing.created_at if existing else now,
            updated_at=now,
        ) if existing else MeetingDelegation(
            meeting_id=meeting.id,
            represented_user_id=request.actor_id,
            represented_user_name=represented.name,
            status="ready",
            mission=mission,
            calendar_etag=meeting.etag,
            policy_snapshot_hash=self._policy_hash(request.actor_id, mission),
            expires_at=max(meeting.end_at + timedelta(minutes=15), now + timedelta(minutes=20)),
            created_at=now,
            updated_at=now,
        )
        self.workspace.save_meeting_delegation(delegation)
        meeting.attendance_plans[request.actor_id] = "agent"
        self.workspace.save_meeting(meeting)
        self.workspace.append_audit(AuditEvent(
            event_type="meeting.delegation_created",
            actor_id=request.actor_id,
            entity_ids=[meeting.id, delegation.id],
            summary=f"{represented.name} assigned their NoBS agent to {meeting.title}.",
            created_at=now,
            metadata={"mode": mission.mode, "capabilities": mission.capability_ids, "calendar_etag": meeting.etag},
        ))
        return delegation

    def set_attendance(self, meeting, actor_id: str, choice: str):
        if actor_id not in meeting.attendee_user_ids and actor_id != meeting.organizer_user_id:
            raise PermissionError("Only a meeting participant can change their attendance plan")
        meeting.attendance_plans[actor_id] = choice
        for attendee in meeting.attendees:
            if attendee.user_id == actor_id:
                # Agent attendance is a private NoBS plan. It must never imply
                # that the human accepted the Google Calendar invitation.
                if choice == "decline":
                    attendee.response_status = "declined"
                elif choice == "attend":
                    attendee.response_status = "accepted"
        existing = self.for_meeting(meeting.id, actor_id)
        if existing and choice == "attend" and existing.status not in {"ended", "revoked"}:
            self.end(existing, revoked=True)
        self.workspace.save_meeting(meeting)
        self.workspace.append_audit(AuditEvent(
            event_type="meeting.attendance_updated",
            actor_id=actor_id,
            entity_ids=[meeting.id],
            summary=f"Attendance plan changed to {choice} for {meeting.title}.",
            created_at=self.now_fn(),
            metadata={"choice": choice, "calendar_rsvp_changed": False},
        ))
        return meeting

    def update(self, delegation: MeetingDelegation, request: MeetingDelegationUpdate) -> MeetingDelegation:
        if delegation.status in {"live", "paused", "reconnecting", "ended", "revoked"}:
            raise RuntimeError("The mission cannot be changed after the live session starts")
        meeting = self.workspace.meetings[delegation.meeting_id]
        delegation.mission = self._mission(
            mode=request.mode,
            tell=request.tell,
            ask=request.ask,
            capability_ids=request.capability_ids,
            escalation_rules=request.escalation_rules,
            participant_user_ids=meeting.attendee_user_ids,
        )
        delegation.policy_snapshot_hash = self._policy_hash(request.actor_id, delegation.mission)
        delegation.updated_at = self.now_fn()
        self.workspace.save_meeting_delegation(delegation)
        return delegation

    def start(self, delegation: MeetingDelegation) -> tuple[MeetingDelegation, LiveMeetingSession, str]:
        meeting = self.workspace.meetings[delegation.meeting_id]
        if meeting.etag != delegation.calendar_etag:
            meeting.preparation_status = "stale"
            self.workspace.save_meeting(meeting)
            raise RuntimeError("The Calendar event changed; confirm the mission again")
        if delegation.status in {"ended", "revoked"}:
            raise RuntimeError("This delegation is no longer active")
        self.expire_abandoned_sessions()
        active = [item for item in self.workspace.live_meeting_sessions.values() if item.status in {"connecting", "live", "paused", "reconnecting"}]
        if len(active) >= self.settings.live_max_concurrent_sessions:
            self.workspace.increment_stat("live_budget_blocks")
            raise RuntimeError("The demo already has an active agent meeting")
        used_seconds = self.used_live_seconds()
        # Preserve capacity to finish sessions already in progress. New work is
        # rejected once the organization reaches 80% of its daily allowance.
        if used_seconds >= self.settings.live_max_org_minutes_per_day * 60 * 0.8:
            self.workspace.increment_stat("live_budget_blocks")
            raise RuntimeError("NoBS is preserving the remaining live-meeting allowance for active sessions")

        nonce = secrets.token_urlsafe(24)
        now = self.now_fn()
        provider = "google_meet" if meeting.conference_uri else "in_app"
        session = LiveMeetingSession(
            delegation_id=delegation.id,
            status="connecting",
            provider=provider,
            conference_uri=meeting.conference_uri,
            join_status="queued" if provider == "google_meet" else "not_started",
            provider_display_name=f"NoBS Agent for {delegation.represented_user_name}",
            join_updated_at=now,
            session_nonce_hash=sha256(nonce.encode()).hexdigest(),
            resume_expires_at=now + timedelta(minutes=20),
            updated_at=now,
        )
        delegation.status = "live"
        delegation.updated_at = now
        self.workspace.save_meeting_delegation(delegation)
        self.workspace.save_live_meeting_session(session)
        self.workspace.increment_stat("live_sessions_started")
        self.workspace.append_audit(AuditEvent(
            event_type="meeting.live_session_started",
            actor_id=delegation.represented_user_id,
            entity_ids=[delegation.meeting_id, delegation.id, session.id],
            summary=f"{delegation.represented_user_name}'s explicitly identified agent was queued for the live meeting.",
            created_at=now,
            metadata={"mode": delegation.mission.mode, "provider": provider, "raw_audio_persisted": False},
        ))
        return delegation, session, nonce

    def claim_bridge_job(self, bridge_id: str) -> dict | None:
        """Lease one Google Meet join without persisting a reusable media credential."""
        now = self.now_fn()
        with self.workspace.lock:
            candidates = sorted(
                (
                    item for item in self.workspace.live_meeting_sessions.values()
                    if item.provider == "google_meet"
                    and item.status == "connecting"
                    and (
                        item.join_status == "queued"
                        or (
                            item.join_status == "joining"
                            and item.bridge_lease_expires_at is not None
                            and item.bridge_lease_expires_at <= now
                        )
                    )
                ),
                key=lambda item: item.updated_at,
            )
            if not candidates:
                return None
            session = candidates[0]
            delegation = self.workspace.meeting_delegations[session.delegation_id]
            meeting = self.workspace.meetings[delegation.meeting_id]
            nonce = secrets.token_urlsafe(24)
            session.session_nonce_hash = sha256(nonce.encode()).hexdigest()
            session.bridge_id = bridge_id
            session.bridge_lease_expires_at = now + timedelta(minutes=2)
            session.join_status = "joining"
            session.join_error = None
            session.join_updated_at = now
            session.updated_at = now
            self.workspace.save_live_meeting_session(session)
        self.workspace.append_audit(AuditEvent(
            event_type="meeting.bridge_job_claimed",
            actor_id=delegation.represented_user_id,
            entity_ids=[meeting.id, delegation.id, session.id],
            summary=f"Meet bridge {bridge_id} claimed the bounded join request.",
            created_at=now,
            metadata={"bridge_id": bridge_id, "provider": "google_meet"},
        ))
        return {
            "session_id": session.id,
            "delegation_id": delegation.id,
            "represented_user_id": delegation.represented_user_id,
            "represented_user_name": delegation.represented_user_name,
            "participant_display_name": session.provider_display_name,
            "meeting_id": meeting.id,
            "meeting_title": meeting.title,
            "conference_uri": session.conference_uri,
            "session_nonce": nonce,
            "resume_expires_at": session.resume_expires_at,
        }

    def update_bridge_status(
        self,
        session_id: str,
        *,
        bridge_id: str,
        status: str,
        participant_id: str | None = None,
        participant_display_name: str | None = None,
        error: str | None = None,
    ) -> LiveMeetingSession:
        session = self.workspace.live_meeting_sessions.get(session_id)
        if not session or session.provider != "google_meet":
            raise KeyError("Google Meet live session not found")
        if session.bridge_id != bridge_id:
            raise PermissionError("This bridge does not own the live-session lease")
        now = self.now_fn()
        session.join_status = status
        session.join_error = error if status == "failed" else None
        session.provider_participant_id = participant_id or session.provider_participant_id
        session.provider_display_name = participant_display_name or session.provider_display_name
        session.join_updated_at = now
        session.updated_at = now
        delegation = self.workspace.meeting_delegations[session.delegation_id]
        if status == "live":
            session.started_at = session.started_at or now
            session.bridge_lease_expires_at = session.resume_expires_at
            delegation.status = "live"
        elif status == "ended":
            session.status = "ended"
        elif status == "failed":
            session.status = "failed"
            delegation.status = "failed"
        delegation.updated_at = now
        self.workspace.save_live_meeting_session(session)
        self.workspace.save_meeting_delegation(delegation)
        self.workspace.append_audit(AuditEvent(
            event_type=f"meeting.bridge_{status}",
            actor_id=delegation.represented_user_id,
            entity_ids=[delegation.meeting_id, delegation.id, session.id],
            summary=f"Google Meet bridge state changed to {status}.",
            created_at=now,
            metadata={"bridge_id": bridge_id, "participant_id": participant_id or "", "error": error or ""},
        ))
        if status == "ended" and self.handoff(delegation) is None:
            self.end(delegation)
        return session

    def session_for(self, delegation_id: str) -> LiveMeetingSession | None:
        matches = [item for item in self.workspace.live_meeting_sessions.values() if item.delegation_id == delegation_id]
        return max(matches, key=lambda item: item.updated_at) if matches else None

    def expire_abandoned_sessions(self) -> None:
        now = self.now_fn()
        expired = [
            item for item in self.workspace.live_meeting_sessions.values()
            if item.status in {"connecting", "reconnecting"} and now > item.resume_expires_at
        ]
        for session in expired:
            delegation = self.workspace.meeting_delegations.get(session.delegation_id)
            if not delegation or delegation.status in {"ended", "revoked", "failed"}:
                session.status = "failed"
                session.updated_at = now
                self.workspace.save_live_meeting_session(session)
                continue
            self._record(
                session,
                "action",
                "The secure reconnect window expired; available outcomes were preserved for follow-up.",
            )
            self.end(delegation)

    def verify_nonce(self, session: LiveMeetingSession, nonce: str) -> bool:
        return (
            self.now_fn() <= session.resume_expires_at
            and secrets.compare_digest(session.session_nonce_hash, sha256(nonce.encode()).hexdigest())
        )

    def set_session_state(self, session: LiveMeetingSession, delegation: MeetingDelegation, state: str) -> None:
        session.status = state
        session.updated_at = self.now_fn()
        delegation.status = "paused" if state == "paused" else "live" if state == "live" else delegation.status
        delegation.updated_at = self.now_fn()
        self.workspace.save_live_meeting_session(session)
        self.workspace.save_meeting_delegation(delegation)

    def open_connection(self, session: LiveMeetingSession) -> None:
        now = self.now_fn()
        session.started_at = session.started_at or now
        session.connection_started_at = session.connection_started_at or now
        if session.provider == "google_meet":
            session.join_status = "live"
            session.join_updated_at = now
        session.updated_at = now
        self.workspace.save_live_meeting_session(session)

    def close_connection(self, session: LiveMeetingSession) -> None:
        if session.connection_started_at is None:
            return
        now = self.now_fn()
        session.active_connection_seconds += max(0.0, (now - session.connection_started_at).total_seconds())
        session.connection_started_at = None
        session.updated_at = now
        self.workspace.save_live_meeting_session(session)

    def add_audio_usage(self, session: LiveMeetingSession, *, input_seconds: float = 0, output_seconds: float = 0) -> None:
        session.input_audio_seconds += max(0, input_seconds)
        session.output_audio_seconds += max(0, output_seconds)
        session.updated_at = self.now_fn()
        self.workspace.save_live_meeting_session(session)

    def record_token_usage(self, session: LiveMeetingSession, usage: dict) -> None:
        input_tokens = int(usage.get("prompt_token_count") or usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("candidates_token_count") or usage.get("output_tokens") or 0)
        input_delta = max(0, input_tokens - session.input_tokens)
        output_delta = max(0, output_tokens - session.output_tokens)
        session.input_tokens = max(session.input_tokens, input_tokens)
        session.output_tokens = max(session.output_tokens, output_tokens)
        session.updated_at = self.now_fn()
        self.workspace.save_live_meeting_session(session)
        if input_delta:
            self.workspace.increment_stat("live_input_tokens", input_delta)
        if output_delta:
            self.workspace.increment_stat("live_output_tokens", output_delta)

    def claim_tool_call(self, session: LiveMeetingSession) -> bool:
        if session.tool_calls >= self.settings.live_max_tool_calls_per_session:
            return False
        session.tool_calls += 1
        session.updated_at = self.now_fn()
        self.workspace.save_live_meeting_session(session)
        self.workspace.increment_stat("live_tool_calls")
        return True

    def used_live_seconds(self) -> float:
        now = self.now_fn()
        total = 0.0
        for item in self.workspace.live_meeting_sessions.values():
            total += item.active_connection_seconds
            if item.connection_started_at:
                total += max(0.0, (now - item.connection_started_at).total_seconds())
        return total

    def session_seconds_remaining(self, session: LiveMeetingSession) -> float:
        if not session.started_at:
            return float(self.settings.live_max_session_minutes * 60)
        elapsed = max(0.0, (self.now_fn() - session.started_at).total_seconds())
        session_remaining = self.settings.live_max_session_minutes * 60 - elapsed
        org_remaining = self.settings.live_max_org_minutes_per_day * 60 - self.used_live_seconds()
        return max(0.0, min(session_remaining, org_remaining))

    def process_utterance(self, delegation: MeetingDelegation, session: LiveMeetingSession, text: str) -> dict:
        text = " ".join(text.split()).strip()[:2000]
        if not text:
            return {"type": "agent_silent", "reason": "No actionable speech detected"}
        prompt_verdict = self.prompt_guard.screen_prompt(text)
        if not prompt_verdict.allowed:
            return self._escalate(
                delegation,
                session,
                "I blocked untrusted meeting content before it reached the live agent.",
                security=True,
            )
        if any(pattern.search(text) for pattern in _INJECTION_PATTERNS):
            return self._escalate(delegation, session, "I blocked an untrusted instruction and did not use it as meeting context.", security=True)

        lowered = text.lower()
        if any(term in lowered for term in ("salary", "compensation", "private dm", "private message", "performance review")):
            return self._escalate(delegation, session, "I can't share compensation, performance, or private-message information in this meeting.", security=True)
        if any(term in lowered for term in ("change the release date", "move the launch", "approve the security", "security exception", "make the decision")):
            return self._escalate(delegation, session, "That requires human authority. I recorded the context for the represented employee instead of deciding.")
        if "who are you" in lowered or "are you shivam" in lowered:
            response = f"I'm {delegation.represented_user_name}'s NoBS agent, representing them for this meeting. I'm not {delegation.represented_user_name}."
            self._record(session, "answer", response)
            return {"type": "agent_response", "text": response, "evidence_ids": []}
        if delegation.mission.mode == "listen" and delegation.represented_user_name.lower().split()[0] not in lowered and "agent" not in lowered:
            return {"type": "agent_silent", "reason": "Listen mode ignored unrelated discussion"}

        capability = self._capability_for(lowered)
        if capability and capability not in delegation.mission.capability_ids:
            return self._escalate(delegation, session, "That topic is outside the capabilities granted in this mission.")
        if not self.claim_tool_call(session):
            return self._escalate(delegation, session, "The live tool-call limit was reached; I saved this for human follow-up.")
        evidence = self._authorized_evidence(delegation, lowered)
        if not evidence:
            return self._escalate(delegation, session, "I couldn't verify that from context shareable with everyone in this meeting.")
        primary = evidence[0]
        response = primary.content.strip()
        if len(response) > 420:
            response = response[:417].rstrip() + "…"
        response = f"Based on the latest authorized context: {response}"
        response_verdict = self.prompt_guard.screen_response(response)
        if not response_verdict.allowed:
            return self._escalate(
                delegation,
                session,
                "I withheld a generated answer because it did not pass the configured security screen.",
                security=True,
            )
        self._record(session, "answer", response, [item.id for item in evidence[:3]])
        return {"type": "agent_response", "text": response, "evidence_ids": [item.id for item in evidence[:3]]}

    def end(self, delegation: MeetingDelegation, *, revoked: bool = False) -> MeetingHandoff:
        session = self.session_for(delegation.id)
        if session:
            if session.ended_at is None:
                self.close_connection(session)
                session.ended_at = self.now_fn()
                self.workspace.increment_stat("live_active_connection_seconds", int(session.active_connection_seconds))
            session.status = "ended"
            session.updated_at = self.now_fn()
            self.workspace.save_live_meeting_session(session)
        delegation.status = "revoked" if revoked else "ended"
        delegation.updated_at = self.now_fn()
        self.workspace.save_meeting_delegation(delegation)
        outcomes = session.outcomes if session else []
        meeting = self.workspace.meetings[delegation.meeting_id]
        handoff = MeetingHandoff(
            delegation_id=delegation.id,
            meeting_id=meeting.id,
            represented_user_id=delegation.represented_user_id,
            told=delegation.mission.tell,
            asked=delegation.mission.ask,
            answers=[item.summary for item in outcomes if item.kind == "answer"],
            decisions_observed=[item.summary for item in outcomes if item.kind == "decision"],
            for_you=[item.summary for item in outcomes if item.kind in {"action", "escalation"}],
            escalations=[item.summary for item in outcomes if item.kind == "escalation"],
            evidence_ids=sorted({evidence_id for item in outcomes for evidence_id in item.evidence_ids}),
            meeting_minutes_avoided=max(0, int((meeting.end_at - meeting.start_at).total_seconds() // 60)),
            created_at=self.now_fn(),
        )
        self.workspace.save_meeting_handoff(handoff)
        self.workspace.append_audit(AuditEvent(
            event_type="meeting.live_session_ended",
            actor_id=delegation.represented_user_id,
            entity_ids=[meeting.id, delegation.id, handoff.id],
            summary=f"Meeting handoff created with {len(handoff.escalations)} escalation(s).",
            created_at=self.now_fn(),
            metadata={"revoked": revoked, "audio_stored": False, "transcript_stored": False},
        ))
        return handoff

    async def end_with_synthesis(self, delegation: MeetingDelegation, *, revoked: bool = False) -> MeetingHandoff:
        summary = ""
        session = self.session_for(delegation.id)
        model = self.handoff_model
        if session and model and model.expected_calls:
            meeting = self.workspace.meetings[delegation.meeting_id]
            compact = {
                "tell": delegation.mission.tell,
                "ask": delegation.mission.ask,
                "outcomes": [item.model_dump(mode="json") for item in session.outcomes],
                "meeting_minutes": max(0, int((meeting.end_at - meeting.start_at).total_seconds() // 60)),
            }
            evidence = [Evidence(
                id=f"meeting-outcomes-{session.id}",
                title=f"Structured outcomes from {meeting.title}",
                source_type="nobs_live_outcomes",
                source_url="",
                entity_ids=[meeting.id, delegation.represented_user_id],
                scope="meeting_handoff",
                content=json.dumps(compact, ensure_ascii=False, separators=(",", ":")),
                observed_at=self.now_fn(),
                confidence=1.0,
            )]
            prompt = "Summarize this meeting handoff concisely: what was told, asked, answered or decided, what still needs the represented employee, and time saved."
            reservation = None
            if self.usage_guard:
                built_prompt = model.build_prompt(text=prompt, intent=Intent.FACTUAL, evidence=evidence)
                try:
                    reservation = self.usage_guard.reserve(
                        calls=model.expected_calls,
                        input_tokens=estimate_tokens(built_prompt) + estimate_tokens(getattr(model, "INSTRUCTION", "")),
                        output_tokens=model.max_output_tokens,
                    )
                except ModelBudgetExceeded:
                    reservation = None
                    model = None
            if model:
                try:
                    synthesis = await model.synthesize_async(text=prompt, intent=Intent.FACTUAL, evidence=evidence)
                    if reservation and self.usage_guard:
                        self.usage_guard.finalize(reservation, synthesis.usage)
                    verdict = self.prompt_guard.screen_response(synthesis.text)
                    if verdict.allowed:
                        summary = synthesis.text.strip()[:1200]
                except Exception:
                    # An ambiguous provider failure intentionally leaves its
                    # reservation charged so a restart cannot hide spend.
                    self.workspace.append_audit(AuditEvent(
                        event_type="meeting.handoff_synthesis_failed",
                        actor_id=delegation.represented_user_id,
                        entity_ids=[delegation.meeting_id, delegation.id],
                        summary="The optional handoff summary failed; deterministic structured outcomes were preserved.",
                        created_at=self.now_fn(),
                    ))
        handoff = self.end(delegation, revoked=revoked)
        if summary:
            handoff.summary = summary
            self.workspace.save_meeting_handoff(handoff)
        return handoff

    def handoff(self, delegation: MeetingDelegation) -> MeetingHandoff | None:
        matches = [item for item in self.workspace.meeting_handoffs.values() if item.delegation_id == delegation.id]
        return max(matches, key=lambda item: item.created_at) if matches else None

    def _mission(self, *, mode: str, tell: list[str], ask: list[str], capability_ids: list[str], escalation_rules: list[str], participant_user_ids: list[str]) -> MissionPacket:
        capabilities = list(dict.fromkeys(capability_ids))
        invalid = sorted(set(capabilities).difference(ALLOWED_CAPABILITIES))
        if invalid:
            raise ValueError(f"Unknown mission capability: {invalid[0]}")
        sanitized_tell = self._clean_items(tell)
        sanitized_ask = self._clean_items(ask)
        custom_escalations = self._clean_items(escalation_rules)
        mission_text = "\n".join([*sanitized_tell, *sanitized_ask, *custom_escalations])
        if mission_text:
            verdict = self.prompt_guard.screen_prompt(mission_text)
            if not verdict.allowed:
                raise ValueError("Mission content did not pass the configured security screen")
        return MissionPacket(
            mode=mode,
            tell=sanitized_tell,
            ask=sanitized_ask,
            capability_ids=capabilities,
            escalation_rules=list(dict.fromkeys([*MANDATORY_ESCALATIONS, *custom_escalations])),
            participant_user_ids=list(dict.fromkeys(participant_user_ids)),
        )

    @staticmethod
    def _clean_items(values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values[:12]:
            cleaned = " ".join(str(value).split()).strip()[:500]
            if not cleaned:
                continue
            if any(pattern.search(cleaned) for pattern in _INJECTION_PATTERNS):
                raise ValueError("Mission content contains a policy-bypass instruction")
            result.append(cleaned)
        return list(dict.fromkeys(result))

    def _policy_hash(self, actor_id: str, mission: MissionPacket) -> str:
        actor = self.workspace.users[actor_id]
        payload = {"roles": sorted(actor.roles), "projects": sorted(actor.project_ids), "mission": mission.model_dump(mode="json")}
        return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _capability_for(text: str) -> str:
        if any(term in text for term in ("customer", "northstar", "customer-safe")):
            return "share_customer_safe_status"
        if any(term in text for term in ("why", "decision", "decided")):
            return "explain_confirmed_decisions"
        return "answer_project_status"

    def _authorized_evidence(self, delegation: MeetingDelegation, text: str):
        represented = self.workspace.users[delegation.represented_user_id]
        participants = [self.workspace.users[user_id] for user_id in delegation.mission.participant_user_ids if user_id in self.workspace.users]
        words = {word for word in re.findall(r"[a-z0-9-]+", text) if len(word) > 3}
        ranked = []
        for evidence in self.workspace.evidence.values():
            haystack = f"{evidence.title} {evidence.content} {' '.join(evidence.entity_ids)}".lower()
            relevant = bool(words.intersection(set(re.findall(r"[a-z0-9-]+", haystack)))) or "atlas" in haystack
            if not relevant or evidence.security_state == SecurityState.BLOCKED:
                continue
            if not self.policy.can_read(represented, evidence):
                continue
            if any(not self.policy.can_read(participant, evidence) for participant in participants):
                continue
            ranked.append(evidence)
        ranked.sort(key=lambda item: (item.confidence, item.observed_at), reverse=True)
        return ranked[:3]

    def _record(self, session: LiveMeetingSession, kind: str, summary: str, evidence_ids: list[str] | None = None) -> None:
        session.outcomes.append(MeetingOutcomeEntry(kind=kind, summary=summary, evidence_ids=evidence_ids or [], created_at=self.now_fn()))
        session.updated_at = self.now_fn()
        self.workspace.save_live_meeting_session(session)

    def _escalate(self, delegation: MeetingDelegation, session: LiveMeetingSession, message: str, *, security: bool = False) -> dict:
        self._record(session, "escalation", message)
        delegation.status = "escalated"
        delegation.updated_at = self.now_fn()
        self.workspace.save_meeting_delegation(delegation)
        self.workspace.append_audit(AuditEvent(
            event_type="meeting.security_boundary" if security else "meeting.authority_escalated",
            actor_id=delegation.represented_user_id,
            entity_ids=[delegation.meeting_id, delegation.id, session.id],
            summary=message,
            created_at=self.now_fn(),
            metadata={"know": "checked", "share": "denied" if security else "checked", "say": "withheld", "decide": "escalated"},
        ))
        return {"type": "escalation", "text": message, "security": security}
