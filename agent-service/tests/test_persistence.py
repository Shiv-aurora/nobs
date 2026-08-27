from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.persistence import RecordingStateStore
from app.service import Services


def make_client() -> tuple[TestClient, RecordingStateStore]:
    store = RecordingStateStore()
    settings = Settings(
        demo_mode=True,
        workspace_path=Path(__file__).resolve().parents[2] / "seed" / "demo_workspace.json",
        max_user_per_minute=50,
        max_user_per_hour=100,
        max_user_per_day=200,
        max_org_per_minute=100,
        max_org_per_day=500,
        max_concurrent_runs=2,
    )
    services = Services(settings=settings, state_store=store)
    return TestClient(create_app(services)), store


def operation_names(store: RecordingStateStore) -> list[str]:
    return [name for name, _ in store.operations]


def test_answer_persists_stats_trace_and_audit() -> None:
    client, store = make_client()
    response = client.post("/v1/query", json={"requester_id": "maya", "text": "Why is Atlas delayed?"})
    assert response.status_code == 200
    names = operation_names(store)
    assert "query" in names
    assert "audit" in names
    assert names.count("stats") >= 2


def test_decision_resolution_persists_decision_and_scoped_memory() -> None:
    client, store = make_client()
    created = client.post(
        "/v1/query",
        json={"requester_id": "maya", "text": "Can we bypass security review for the $200K customer?"},
    ).json()
    assert "decision" in operation_names(store)

    resolved = client.post(
        f"/v1/decisions/{created['decision_id']}/resolve",
        json={"actor_id": "alex", "status": "rejected", "rationale": "The security control remains mandatory."},
    )
    assert resolved.status_code == 200
    assert "memory" in operation_names(store)
    assert operation_names(store).count("decision") >= 2


def test_work_event_is_idempotent_at_persistence_boundary() -> None:
    client, store = make_client()
    payload = {
        "id": "event-new-review",
        "source": "github",
        "event_type": "pull_request.reviewed",
        "actor_user_id": "daniel",
        "entity_ids": ["daniel", "atlas", "auth-392"],
        "occurred_at": "2026-08-27T14:00:00-04:00",
        "payload": {"review_state": "approved"},
    }
    assert client.post("/v1/events", json=payload).json()["accepted"] is True
    assert client.post("/v1/events", json=payload).json()["accepted"] is False
    persisted = [value for name, value in store.operations if name == "work_event"]
    assert persisted == ["event-new-review"]


def test_demo_reset_clears_dynamic_store() -> None:
    client, store = make_client()
    assert client.post("/v1/demo/reset", json={}).status_code == 200
    assert ("clear", None) in store.operations
