from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ActionCommand(BaseModel):
    id: str
    command_type: Literal["calendar.cancel", "calendar.shorten", "calendar.update_agenda"]
    target_system: Literal["google_calendar"] = "google_calendar"
    target_ref: str
    expected_etag: str
    payload: dict[str, object]
    status: Literal["proposed", "approved", "rejected", "queued", "executing", "succeeded", "failed", "stale"]
    idempotency_key: str
    mission_id: str
    trace_id: str = ""
    checkpoint_id: str
    approval_decision_id: str
    policy_snapshot_hash: str
    expires_at: datetime
    requested_by: str
    approved_by: str
    approved_at: datetime
    attempt_count: int = Field(default=0, ge=0)
    lease_expires_at: datetime | None = None
    applied_etag: str | None = None
    provider_response_hash: str | None = None
    error_code: str | None = None


class CommandAttempt(BaseModel):
    id: str
    command_id: str
    attempt: int
    status: Literal["started", "succeeded", "failed", "stale"]
    started_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None
    provider_response_hash: str | None = None


class ClaimedCommand(BaseModel):
    command: ActionCommand
    execute: bool
    reason: Literal["claimed", "already_succeeded", "active_lease", "terminal", "attempt_limit", "expired", "invalid_approval"]


class ProviderResult(BaseModel):
    applied_etag: str | None = None
    response_hash: str
    verified: bool
