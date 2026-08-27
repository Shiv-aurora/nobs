from __future__ import annotations

from fastapi.testclient import TestClient


def _create_decision(client: TestClient) -> str:
    response = client.post(
        "/v1/query",
        json={
            "requester_id": "maya",
            "text": "A customer will pay $200K. Can we bypass the Atlas security review?",
        },
    )
    assert response.status_code == 200
    return response.json()["decision_id"]


def test_wrong_actor_cannot_resolve_decision(client):
    decision_id = _create_decision(client)
    response = client.post(
        f"/v1/decisions/{decision_id}/resolve",
        json={"actor_id": "maya", "status": "approved", "rationale": "I want it."},
    )
    assert response.status_code == 403


def test_authorized_rejection_becomes_scoped_memory_and_avoids_second_ping(client, services):
    decision_id = _create_decision(client)
    resolution = client.post(
        f"/v1/decisions/{decision_id}/resolve",
        json={
            "actor_id": "alex",
            "status": "rejected",
            "rationale": "SEC-184 must complete; revenue urgency does not justify bypassing the control.",
        },
    )
    assert resolution.status_code == 200
    assert resolution.json()["memory"]["canonical_key"] == "atlas_security_exception"

    repeated = client.post(
        "/v1/query",
        json={"requester_id": "maya", "text": "Can we make the Atlas security exception for the $200K customer?"},
    )
    assert repeated.status_code == 200
    payload = repeated.json()
    assert payload["status"] == "answered"
    assert payload["people_interrupted"] == 0
    assert payload["cached"] is True
    assert "previously rejected" in payload["answer"]
    assert services.workspace.stats["human_interruptions"] == 1
