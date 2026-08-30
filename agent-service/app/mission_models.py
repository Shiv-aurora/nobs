from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class MissionStatus(StrEnum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    QUEUED_ACTION = "queued_action"
    COMPLETED = "completed"
    FAILED = "failed"


class MissionStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentManifest(BaseModel):
    id: str
    version: str
    name: str
    owner: str
    runtime: Literal["google_adk_llm", "deterministic_test_program"]
    deployment_target: str
    deployment_revision: str
    model: str | None = None
    input_schema: str
    output_schema: str
    capabilities: list[str]
    tools: list[str]
    allowed_scopes: list[str]
    runtime_identity: str
    health: Literal["ready", "degraded", "disabled"] = "ready"
    approved: bool = True
    registered_at: datetime


class EvidenceClaim(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"claim-{uuid4().hex[:12]}")
    statement: str
    source_ref: str
    observed_at: datetime
    confidence: float = Field(ge=0, le=1)


class MissionPlan(BaseModel):
    objective: str
    agenda_routes: dict[str, list[str]]
    specialist_ids: list[str]
    authority_required: bool


class SpecialistReport(BaseModel):
    agent_id: str
    agent_version: str
    agenda_item_ids: list[str]
    findings: list[str]
    claims: list[EvidenceClaim]
    unresolved_questions: list[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime
    duration_ms: float = Field(ge=0)


class CriticReport(BaseModel):
    accepted_claim_ids: list[str]
    rejected_claim_ids: list[str]
    conflicts: list[str]
    unresolved_questions: list[str]


class AgendaResolution(BaseModel):
    agenda_item_id: str
    status: Literal["resolved", "needs_human", "open"]
    resolution: str
    evidence_claim_ids: list[str]
    authority_type: Literal["atlas_security_approval"] | None = None


class MissionRecommendation(BaseModel):
    disposition: Literal["cancel", "shorten", "keep"]
    duration_minutes: int = Field(ge=0, le=480)
    rationale: str
    humans_required: int = Field(ge=0)


class ProposedCommand(BaseModel):
    id: str = Field(default_factory=lambda: f"command-{uuid4().hex[:12]}")
    command_type: Literal["calendar.cancel", "calendar.shorten", "calendar.update_agenda"]
    target_system: Literal["google_calendar"] = "google_calendar"
    target_ref: str
    expected_etag: str
    payload: dict[str, object]
    status: Literal["proposed", "approved", "rejected", "queued", "succeeded", "failed", "stale"] = "proposed"
    idempotency_key: str
    mission_id: str
    trace_id: str
    checkpoint_id: str | None = None
    business_checkpoint_id: str | None = None
    approval_decision_id: str | None = None
    policy_snapshot_hash: str
    expires_at: datetime
    requested_by: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    attempt_count: int = Field(default=0, ge=0)
    lease_expires_at: datetime | None = None
    applied_etag: str | None = None
    provider_response_hash: str | None = None
    error_code: str | None = None


class HumanCheckpoint(BaseModel):
    id: str = Field(default_factory=lambda: f"checkpoint-{uuid4().hex[:12]}")
    mission_id: str
    checkpoint_type: Literal["meeting_disposition", "calendar_write", "restricted_decision"]
    status: Literal["pending", "approved", "rejected"] = "pending"
    summary: str
    authorized_actor_ids: list[str]
    authority_type: Literal["atlas_security_approval"] | None = None
    command_ids: list[str]
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    rationale: str | None = None


class MissionStep(BaseModel):
    id: str = Field(default_factory=lambda: f"step-{uuid4().hex[:12]}")
    mission_id: str
    ordinal: int
    node_id: str
    node_kind: Literal["access_gate", "controller", "specialist", "critic", "synthesizer", "authority_gate", "business_decision_gate", "calendar_action_gate", "command_builder", "result_verifier"]
    status: MissionStepStatus
    agent_id: str | None = None
    agent_version: str | None = None
    attempt: int = Field(default=1, ge=1)
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    error_code: str | None = None


class MissionRun(BaseModel):
    id: str = Field(default_factory=lambda: f"mission-{uuid4().hex[:12]}")
    meeting_id: str
    organization_id: str = "acme"
    mission_type: Literal["meeting_resolution"] = "meeting_resolution"
    workflow_version: str = "1.0.0"
    policy_version: str = "1.0.0"
    model_id: str
    trigger: Literal["manual", "scheduled"]
    started_by: str
    status: MissionStatus = MissionStatus.ACCEPTED
    current_stage: str = "accepted"
    meeting_etag: str
    plan: MissionPlan | None = None
    specialist_reports: list[SpecialistReport] = Field(default_factory=list)
    critic_report: CriticReport | None = None
    resolutions: list[AgendaResolution] = Field(default_factory=list)
    recommendation: MissionRecommendation | None = None
    proposed_commands: list[ProposedCommand] = Field(default_factory=list)
    business_checkpoint_id: str | None = None
    calendar_checkpoint_id: str | None = None
    checkpoint_id: str | None = None
    quarantined_evidence_count: int = Field(default=0, ge=0)
    trace_id: str
    deadline_at: datetime
    retry_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None


class MissionCheckpointResolution(BaseModel):
    actor_id: str
    decision: Literal["approved", "rejected"]
    rationale: str = Field(min_length=2, max_length=1000)


class ExecutableRegistryResponse(BaseModel):
    agents: list[AgentManifest]
    source: Literal["local_manifest", "google_agent_registry"]
    source_detail: str
