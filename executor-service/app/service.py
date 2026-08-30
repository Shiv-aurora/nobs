from __future__ import annotations

import logging
from datetime import datetime, timezone

from .calendar import CalendarAdapter, StaleETag
from .config import Settings
from .models import CommandAttempt
from .observability import event, executor_span
from .store import CommandStore


logger = logging.getLogger(__name__)


class ActionExecutor:
    def __init__(self, settings: Settings, store: CommandStore, calendar: CalendarAdapter, now_fn=None):
        self.settings = settings
        self.store = store
        self.calendar = calendar
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def execute(self, command_id: str) -> dict[str, object]:
        now = self.now_fn()
        claimed = self.store.claim(command_id, now, self.settings.lease_seconds, self.settings.max_attempts)
        command = claimed.command
        if not claimed.execute:
            event(logger, "command.noop", command_id=command.id, mission_id=command.mission_id, reason=claimed.reason)
            return {"command_id": command.id, "status": command.status, "executed": False, "reason": claimed.reason}
        attempt = CommandAttempt(
            id=f"{command.id}-attempt-{command.attempt_count}",
            command_id=command.id,
            attempt=command.attempt_count,
            status="started",
            started_at=now,
        )
        try:
            with executor_span(
                "command.execute",
                command_id=command.id,
                mission_id=command.mission_id,
                command_type=command.command_type,
                origin_trace_id=command.trace_id,
                attempt=command.attempt_count,
            ):
                result = self.calendar.apply(command)
            if not result.verified:
                raise RuntimeError("Calendar postcondition verification failed")
            command.status = "succeeded"
            command.applied_etag = result.applied_etag
            command.provider_response_hash = result.response_hash
            command.lease_expires_at = None
            attempt.status = "succeeded"
            attempt.provider_response_hash = result.response_hash
            attempt.completed_at = self.now_fn()
            self.store.finish(command, attempt)
            event(logger, "command.succeeded", command_id=command.id, mission_id=command.mission_id, attempt=command.attempt_count)
            return {"command_id": command.id, "status": command.status, "executed": True, "verified": True}
        except StaleETag:
            command.status = "stale"
            command.error_code = "STALE_ETAG"
            command.lease_expires_at = None
            attempt.status = "stale"
            attempt.error_code = command.error_code
            attempt.completed_at = self.now_fn()
            self.store.finish(command, attempt)
            event(logger, "command.stale", command_id=command.id, mission_id=command.mission_id, attempt=command.attempt_count)
            return {"command_id": command.id, "status": command.status, "executed": False, "reason": "stale_etag"}
        except Exception as exc:
            command.status = "failed" if command.attempt_count >= self.settings.max_attempts else "queued"
            command.error_code = type(exc).__name__
            command.lease_expires_at = None
            attempt.status = "failed"
            attempt.error_code = command.error_code
            attempt.completed_at = self.now_fn()
            self.store.finish(command, attempt)
            event(
                logger,
                "command.failed",
                level=logging.ERROR,
                command_id=command.id,
                mission_id=command.mission_id,
                attempt=command.attempt_count,
                error_code=command.error_code,
            )
            raise
