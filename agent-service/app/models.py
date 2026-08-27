from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


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
    id: str
    source: str
    event_type: str
    actor_user_id: str
    entity_ids: list[str]
    occurred_at: datetime
    payload: dict[str, Any]


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
    duration_ms: int = 0


class QueryRequest(BaseModel):
    requester_id: str
    text: str = Field(min_length=3, max_length=2000)
    team_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


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
