from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class Intent(StrEnum):
    FACTUAL = "factual"
    LIVE_STATUS = "live_status"
    POLICY = "policy"
    DECISION = "decision"
    RESTRICTED = "restricted"


class RunStatus(StrEnum):
    RUNNING = "running"
    ANSWERED = "answered"
    ESCALATED = "escalated"
    REFUSED = "refused"
    FAILED = "failed"


class DecisionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISCUSS = "discuss"


class SecurityState(StrEnum):
    TRUSTED = "trusted"
    BLOCKED = "blocked"


class Availability(BaseModel):
    status: str
    until: datetime | None = None
    delegate_user_id: str | None = None


class User(BaseModel):
    id: str
    name: str
    title: str
    team_ids: list[str]
    roles: list[str]
    project_ids: list[str]
    availability: Availability
    avatar: str


class Team(BaseModel):
    id: str
    name: str
    member_ids: list[str]
    purpose: str


class Project(BaseModel):
    id: str
    name: str
    summary: str
    owner_user_id: str
    team_ids: list[str]
    status: str
    health: str
    blocker_ids: list[str]
    target_date: str


class WorkItem(BaseModel):
    id: str
    key: str
    title: str
    project_id: str
    owner_user_id: str
    status: str
    priority: str
    updated_at: datetime
    url: str


class Policy(BaseModel):
    id: str
    key: str
    title: str
    statement: str
    required_role: str
    acting_role: str
    scope: str
    updated_at: datetime


class Delegation(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    authority: str
    starts_at: datetime
    ends_at: datetime
    reason: str


class Evidence(BaseModel):
    id: str
    title: str
    source_type: str
    source_url: str
    entity_ids: list[str]
    scope: str
    content: str
    observed_at: datetime
    confidence: float = Field(ge=0, le=1)
    allowed_roles: list[str] = Field(default_factory=list)
    security_state: SecurityState = SecurityState.TRUSTED
    security_reason: str | None = None


class WorkEvent(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    id: str
    source: str
    event_type: str
    actor_user_id: str
    entity_ids: list[str]
    occurred_at: datetime
    payload: dict[str, Any]
    source_event_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    data_classification: Literal["work_metadata", "confidential", "restricted"] = "work_metadata"

    @model_validator(mode="after")
    def validate_normalized_contract(self) -> "WorkEvent":
        encoded = str(self.payload)
        if len(encoded) > 16_000:
            raise ValueError("WorkEvent payload exceeds the compact metadata limit")
        forbidden = {"password", "secret", "access_token", "refresh_token", "authorization", "cookie"}
        if forbidden.intersection(key.lower() for key in self.payload):
            raise ValueError("WorkEvent payload contains a forbidden credential field")
        return self


class Delegate(BaseModel):
    id: str
    name: str
    kind: Literal["personal", "project", "team", "policy", "router", "authority"]
    entity_id: str
    capabilities: list[str]
    data_scopes: list[str]
    owner_user_id: str | None = None
    status: str = "ready"


class RouteStep(BaseModel):
    ordinal: int
    delegate_id: str
    delegate_name: str
    reason: str
    outcome: str
    step_type: Literal["logical_delegate", "deterministic_policy"] = "logical_delegate"
    duration_ms: float = Field(ge=0)


class QueryRequest(BaseModel):
    requester_id: str
    # Short conversational turns such as "hi" are valid in native messaging.
    # Authorization and rate limiting still run before any model execution.
    text: str = Field(min_length=1, max_length=2000)
    team_id: str | None = None
    delegate_for_user_id: str | None = None
    conversation_context: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class DelegationResolutionRequest(BaseModel):
    requester_id: str
    text: str = Field(min_length=1, max_length=2000)
    conversation_context: dict[str, Any] = Field(default_factory=dict)


class DelegationResolution(BaseModel):
    eligible: bool
    kind: Literal["personal", "organization"] | None = None
    represented_user_id: str | None = None
    represented_user_name: str | None = None
    scope: str | None = None
    reason: str
    confidence: float = Field(ge=0, le=1)


class DecisionOption(BaseModel):
    id: str
    label: str
    tone: Literal["positive", "negative", "neutral"]


class Decision(BaseModel):
    id: str = Field(default_factory=lambda: f"decision-{uuid4().hex[:12]}")
    canonical_key: str
    title: str
    summary: str
    requester_id: str
    assignee_id: str
    project_id: str | None = None
    status: DecisionStatus = DecisionStatus.PENDING
    options: list[DecisionOption]
    evidence_ids: list[str]
    policy_ids: list[str]
    created_at: datetime
    due_at: datetime | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    rationale: str | None = None
    facts_hash: str
    handoff_packet_id: str | None = None


class DecisionResolution(BaseModel):
    actor_id: str
    status: Literal["approved", "rejected", "discuss"]
    rationale: str = Field(min_length=2, max_length=2000)


class DecisionMemory(BaseModel):
    id: str = Field(default_factory=lambda: f"memory-{uuid4().hex[:12]}")
    canonical_key: str
    project_id: str | None
    outcome: str
    rationale: str
    decided_by: str
    source_decision_id: str
    facts_hash: str
    created_at: datetime
    expires_at: datetime


class MeetingAttendee(BaseModel):
    user_id: str
    name: str
    role: str
    response_status: Literal["accepted", "tentative", "declined", "needs_action"] = "accepted"
    agent_status: Literal["ready", "consulting", "done", "skipped"] = "ready"


class AgendaItem(BaseModel):
    id: str
    title: str
    owner_user_id: str | None = None
    status: Literal["open", "resolved", "needs_human", "skipped"] = "open"
    resolution: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class AgentTurn(BaseModel):
    id: str = Field(default_factory=lambda: f"turn-{uuid4().hex[:12]}")
    ordinal: int
    agent_name: str
    agent_kind: Literal["personal", "project", "team", "policy", "authority", "integration"]
    phase: Literal["routed", "retrieved", "work_action", "synthesizing", "completed"]
    conclusion: str
    evidence_ids: list[str] = Field(default_factory=list)
    open_question: str | None = None
    next_agent: str | None = None
    created_at: datetime


class WorkAction(BaseModel):
    id: str = Field(default_factory=lambda: f"action-{uuid4().hex[:12]}")
    kind: Literal["github_issue", "coding_agent", "github_pull_request", "calendar_update", "message_share"]
    provider: str
    title: str
    status: Literal["queued", "investigating", "testing", "blocked", "completed"]
    summary: str
    source_url: str | None = None
    workroom_channel: str | None = None


class MeetingBrief(BaseModel):
    summary: str
    resolved_items: list[str]
    remaining_items: list[str]
    proposed_actions: list[str]
    recommended_disposition: Literal["cancel", "shorten", "keep"]
    recommended_duration_minutes: int = Field(ge=0, le=480)
    original_duration_minutes: int = Field(ge=0, le=1440)
    minutes_saved: int = Field(ge=0)
    humans_required: int = Field(ge=0)


class MeetingPrepRun(BaseModel):
    id: str = Field(default_factory=lambda: f"meeting-run-{uuid4().hex[:12]}")
    meeting_id: str
    mission_id: str | None = None
    trace_id: str | None = None
    status: Literal["accepted", "screened", "routed", "retrieved", "agent_turn", "work_action", "synthesizing", "completed", "failed"]
    trigger: Literal["manual", "scheduled"]
    started_by: str
    turns: list[AgentTurn]
    work_actions: list[WorkAction]
    security_findings: list[SecurityFinding] = Field(default_factory=list)
    brief: MeetingBrief | None = None
    created_at: datetime
    completed_at: datetime | None = None


class Meeting(BaseModel):
    id: str
    calendar_event_id: str
    title: str
    description: str
    start_at: datetime
    end_at: datetime
    organizer_user_id: str
    attendee_user_ids: list[str]
    attendees: list[MeetingAttendee]
    agenda: list[AgendaItem]
    preparation_eligibility: Literal["eligible", "skipped", "ambiguous"]
    preparation_reason: str
    preparation_status: Literal["not_started", "running", "completed", "skipped", "stale"] = "not_started"
    prep_run_id: str | None = None
    workroom_channel: str | None = None
    etag: str
    updated_at: datetime
    source: Literal["google_calendar", "demo"] = "demo"
    confirmed_action: Literal["none", "cancelled", "shortened", "agenda_updated"] = "none"
    pending_action: Literal["none", "cancel", "shorten", "update_agenda"] = "none"
    approved_recommendation: Literal["none", "cancel", "shorten", "update_agenda"] = "none"
    attendance_plans: dict[str, Literal["attend", "agent", "decline"]] = Field(default_factory=dict)


class MeetingPreparationRequest(BaseModel):
    actor_id: str
    trigger: Literal["manual", "scheduled"] = "manual"


class MeetingAttendanceRequest(BaseModel):
    actor_id: str
    # `agent` is a NoBS attendance plan, not a Google Calendar RSVP.
    choice: Literal["attend", "agent", "decline"]


class MeetingActionRequest(BaseModel):
    actor_id: str
    action: Literal["cancel", "shorten", "update_agenda"]
    expected_etag: str
    applied_etag: str | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    agenda: list[str] = Field(default_factory=list)


class MissionPacket(BaseModel):
    mode: Literal["listen", "represent", "mission"] = "represent"
    tell: list[str] = Field(default_factory=list, max_length=12)
    ask: list[str] = Field(default_factory=list, max_length=12)
    capability_ids: list[Literal[
        "answer_project_status",
        "explain_confirmed_decisions",
        "share_customer_safe_status",
        "record_follow_up",
    ]] = Field(default_factory=list, max_length=8)
    escalation_rules: list[str] = Field(default_factory=list, max_length=12)
    participant_user_ids: list[str] = Field(default_factory=list)


class MeetingDelegationCreate(BaseModel):
    actor_id: str
    mode: Literal["listen", "represent", "mission"] = "represent"
    tell: list[str] = Field(default_factory=list)
    ask: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    escalation_rules: list[str] = Field(default_factory=list)
    expected_etag: str


class MeetingDelegationUpdate(BaseModel):
    actor_id: str
    mode: Literal["listen", "represent", "mission"]
    tell: list[str] = Field(default_factory=list)
    ask: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    escalation_rules: list[str] = Field(default_factory=list)


class MeetingDelegationAction(BaseModel):
    actor_id: str


class MeetingDelegation(BaseModel):
    id: str = Field(default_factory=lambda: f"delegation-{uuid4().hex[:12]}")
    meeting_id: str
    represented_user_id: str
    represented_user_name: str
    status: Literal["draft", "ready", "live", "paused", "reconnecting", "ended", "escalated", "failed", "revoked"] = "ready"
    mission: MissionPacket
    calendar_etag: str
    policy_snapshot_hash: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


class MeetingOutcomeEntry(BaseModel):
    kind: Literal["told", "asked", "answer", "decision", "action", "escalation"]
    summary: str = Field(min_length=2, max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime


class LiveMeetingSession(BaseModel):
    id: str = Field(default_factory=lambda: f"live-{uuid4().hex[:12]}")
    delegation_id: str
    status: Literal["created", "connecting", "live", "paused", "reconnecting", "ended", "failed"] = "created"
    session_nonce_hash: str
    resumption_handle: str | None = None
    resume_expires_at: datetime
    started_at: datetime | None = None
    connection_started_at: datetime | None = None
    ended_at: datetime | None = None
    updated_at: datetime
    active_connection_seconds: float = Field(default=0, ge=0)
    input_audio_seconds: float = Field(default=0, ge=0)
    output_audio_seconds: float = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    reconnect_attempts: int = Field(default=0, ge=0)
    outcomes: list[MeetingOutcomeEntry] = Field(default_factory=list)


class MeetingHandoff(BaseModel):
    id: str = Field(default_factory=lambda: f"meeting-handoff-{uuid4().hex[:12]}")
    delegation_id: str
    meeting_id: str
    represented_user_id: str
    summary: str = ""
    told: list[str] = Field(default_factory=list)
    asked: list[str] = Field(default_factory=list)
    answers: list[str] = Field(default_factory=list)
    decisions_observed: list[str] = Field(default_factory=list)
    for_you: list[str] = Field(default_factory=list)
    escalations: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    meeting_minutes_avoided: int = Field(default=0, ge=0)
    created_at: datetime


class HandoffPacket(BaseModel):
    id: str = Field(default_factory=lambda: f"handoff-{uuid4().hex[:12]}")
    question: str
    scope: str
    requested_judgment: str
    evidence_ids: list[str]
    conclusions: list[str]
    uncertainty: list[str]
    security_boundaries: list[str]
    attempted_routes: list[str]
    created_by: str
    created_at: datetime


class KnowledgeMemory(BaseModel):
    id: str = Field(default_factory=lambda: f"knowledge-{uuid4().hex[:12]}")
    canonical_key: str
    scope: str
    answer: str
    evidence_ids: list[str]
    confirmed_by: str
    facts_hash: str
    created_at: datetime
    expires_at: datetime


class OOOQueueItem(BaseModel):
    id: str = Field(default_factory=lambda: f"ooo-{uuid4().hex[:12]}")
    user_id: str
    source_type: Literal["message", "decision", "meeting"]
    source_id: str
    title: str
    summary: str
    urgent: bool = False
    handled_by_agent: bool = False
    created_at: datetime


class OOOQueueCreate(BaseModel):
    user_id: str
    source_type: Literal["message", "decision", "meeting"]
    source_id: str
    title: str
    summary: str
    urgent: bool = False
    handled_by_agent: bool = False


class OOOUpdateRequest(BaseModel):
    actor_id: str
    enabled: bool
    until: datetime | None = None
    delegate_user_id: str | None = None


class SemanticWorkState(BaseModel):
    entity_id: str
    entity_type: Literal["person", "project", "team", "work_item"]
    headline: str
    detail: str
    status: str
    confidence: float = Field(ge=0, le=1)
    source_event_ids: list[str]
    updated_at: datetime


class SecurityFinding(BaseModel):
    evidence_id: str
    category: str
    severity: Literal["low", "medium", "high", "critical"]
    reason: str
    blocked: bool


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"audit-{uuid4().hex[:12]}")
    event_type: str
    actor_id: str
    entity_ids: list[str]
    summary: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryResult(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run-{uuid4().hex[:12]}")
    requester_id: str
    query: str
    intent: Intent
    status: RunStatus
    answer: str
    headline: str
    route: list[RouteStep]
    evidence: list[Evidence]
    confidence: float = Field(ge=0, le=1)
    freshness_label: str
    people_interrupted: int
    decision_id: str | None = None
    decision_assignee_id: str | None = None
    policy_result: str | None = None
    security_findings: list[SecurityFinding] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime
    cached: bool = False
    model_name: str | None = None
    model_calls: int = 0
    model_input_tokens: int = 0
    model_output_tokens: int = 0
    model_cached_input_tokens: int = 0


class BootstrapResponse(BaseModel):
    organization_id: str
    current_user: User
    projects: list[Project]
    needs_you: list[Decision]
    work_states: list[SemanticWorkState]
    attention_metrics: dict[str, int | float]


class RegistryResponse(BaseModel):
    delegates: list[Delegate]
    relationships: list[dict[str, str]]


class HealthResponse(BaseModel):
    status: str
    mode: str
    ai_enabled: bool
    version: str
