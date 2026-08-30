from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.calendar import CalendarAdapter, StaleETag
from app.config import Settings
from app.main import create_app
from app.models import ActionCommand, ProviderResult
from app.service import ActionExecutor
from app.store import MemoryCommandStore


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def command(command_id: str = "command-1") -> ActionCommand:
    return ActionCommand(
        id=command_id,
        command_type="calendar.shorten",
        target_ref="calendar:event-1",
        expected_etag='"etag-1"',
        payload={"duration_minutes": 15},
        status="queued",
        idempotency_key="idem-1",
        mission_id="mission-1",
        checkpoint_id="checkpoint-1",
        requested_by="maya",
        approved_by="shivam",
        approved_at=NOW,
    )


class FakeCalendar(CalendarAdapter):
    def __init__(self, outcome: str = "success"):
        self.outcome = outcome
        self.calls = 0

    def apply(self, action: ActionCommand) -> ProviderResult:
        self.calls += 1
        if self.outcome == "stale":
            raise StaleETag("stale")
        if self.outcome == "error":
            raise RuntimeError("provider unavailable")
        return ProviderResult(applied_etag='"etag-2"', response_hash="hash", verified=True)


def runtime(item: ActionCommand, calendar: FakeCalendar) -> tuple[ActionExecutor, MemoryCommandStore]:
    store = MemoryCommandStore([item])
    settings = Settings(project_id="test", lease_seconds=60, max_attempts=3)
    return ActionExecutor(settings, store, calendar, now_fn=lambda: NOW), store


def test_success_is_verified_and_duplicate_delivery_does_not_execute_twice() -> None:
    calendar = FakeCalendar()
    executor, store = runtime(command(), calendar)

    first = executor.execute("command-1")
    second = executor.execute("command-1")

    assert first == {"command_id": "command-1", "status": "succeeded", "executed": True, "verified": True}
    assert second["reason"] == "already_succeeded"
    assert calendar.calls == 1
    assert store.commands["command-1"].provider_response_hash == "hash"
    assert list(store.attempts) == ["command-1-attempt-1"]


def test_stale_etag_is_terminal_and_never_retried() -> None:
    calendar = FakeCalendar("stale")
    executor, store = runtime(command(), calendar)

    result = executor.execute("command-1")
    duplicate = executor.execute("command-1")

    assert result["status"] == "stale"
    assert store.commands["command-1"].error_code == "STALE_ETAG"
    assert duplicate["reason"] == "terminal"
    assert calendar.calls == 1


def test_active_lease_prevents_concurrent_execution() -> None:
    item = command()
    item.status = "executing"
    item.lease_expires_at = NOW + timedelta(seconds=30)
    calendar = FakeCalendar()
    executor, _ = runtime(item, calendar)

    result = executor.execute("command-1")

    assert result["reason"] == "active_lease"
    assert calendar.calls == 0


def test_transient_failure_requeues_until_attempt_limit() -> None:
    calendar = FakeCalendar("error")
    executor, store = runtime(command(), calendar)

    for attempt in range(1, 4):
        try:
            executor.execute("command-1")
        except RuntimeError:
            pass
        assert store.commands["command-1"].attempt_count == attempt
    assert store.commands["command-1"].status == "failed"
    final = executor.execute("command-1")
    assert final["reason"] == "terminal"
    assert calendar.calls == 3


def test_pubsub_endpoint_accepts_command_id_only() -> None:
    calendar = FakeCalendar()
    executor, _ = runtime(command(), calendar)
    client = TestClient(create_app(executor))
    encoded = base64.b64encode(json.dumps({"schema_version": "1", "command_id": "command-1"}).encode()).decode()

    response = client.post("/v1/commands/pubsub", json={"message": {"data": encoded, "message_id": "msg-1"}})

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
