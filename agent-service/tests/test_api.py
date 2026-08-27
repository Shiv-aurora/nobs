from __future__ import annotations


def test_health_and_bootstrap(client):
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "mode": "demo", "ai_enabled": True, "version": "0.1.0"}

    bootstrap = client.get("/v1/bootstrap", params={"user_id": "maya"})
    assert bootstrap.status_code == 200
    payload = bootstrap.json()
    assert payload["current_user"]["id"] == "maya"
    assert payload["projects"][0]["id"] == "atlas"
    assert any(state["entity_id"] == "daniel" for state in payload["work_states"])


def test_registry_has_logical_delegate_per_person_project_team(client):
    response = client.get("/v1/registry")
    assert response.status_code == 200
    delegates = response.json()["delegates"]
    ids = {item["id"] for item in delegates}
    assert "delegate:user:sarah" in ids
    assert "delegate:project:atlas" in ids
    assert "delegate:team:security" in ids
    assert "delegate:router" in ids
    assert len(delegates) >= 13


def test_work_event_ingestion_is_idempotent(client):
    event = {
        "id": "event-pr-892-reviewed-test",
        "source": "github",
        "event_type": "pull_request.reviewed",
        "actor_user_id": "daniel",
        "entity_ids": ["atlas", "auth-392"],
        "occurred_at": "2026-08-27T13:20:00-04:00",
        "payload": {"number": 892, "review_state": "approved", "mergeable": True},
    }
    first = client.post("/v1/events", json=event)
    second = client.post("/v1/events", json=event)
    assert first.status_code == 200
    assert first.json()["accepted"] is True
    assert second.json()["accepted"] is False
    states = first.json()["states"]
    daniel = next(item for item in states if item["entity_id"] == "daniel")
    assert daniel["status"] == "ready_to_merge"


def test_query_result_can_be_read_back(client):
    response = client.post("/v1/query", json={"requester_id": "maya", "text": "Why is Atlas blocked?"})
    run_id = response.json()["run_id"]
    fetched = client.get(f"/v1/runs/{run_id}")
    assert fetched.status_code == 200
    assert fetched.json()["run_id"] == run_id
