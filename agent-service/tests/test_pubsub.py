from __future__ import annotations

import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.pubsub import PubSubTokenVerifier
from app.service import Services


def encode(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload).encode()).decode()


def envelope(payload: dict, message_id: str = "msg-1") -> dict:
    return {
        "message": {"data": encode(payload), "messageId": message_id},
        "subscription": "projects/test/subscriptions/work-events-push",
    }


def work_event(event_id: str = "pubsub-event-1") -> dict:
    return {
        "id": event_id,
        "source": "github",
        "event_type": "pull_request.reviewed",
        "actor_user_id": "daniel",
        "entity_ids": ["daniel", "atlas", "auth-392"],
        "occurred_at": "2026-08-27T14:00:00-04:00",
        "payload": {"review_state": "approved"},
    }


def test_demo_pubsub_push_decodes_and_deduplicates(client) -> None:
    first = client.post("/v1/events/pubsub", json=envelope(work_event()))
    second = client.post("/v1/events/pubsub", json=envelope(work_event(), "msg-2"))
    assert first.status_code == 200
    assert first.json()["accepted"] is True
    assert first.json()["message_id"] == "msg-1"
    assert second.json()["accepted"] is False


def test_pubsub_rejects_malformed_data(client) -> None:
    payload = {"message": {"data": "not-base64", "messageId": "bad"}, "subscription": "sub"}
    response = client.post("/v1/events/pubsub", json=payload)
    assert response.status_code == 400


def test_pubsub_token_verifier_pins_audience_and_service_account() -> None:
    calls: list[tuple[str, str]] = []

    def validator(token: str, audience: str):
        calls.append((token, audience))
        return {"email": "pubsub-push@example.iam.gserviceaccount.com", "email_verified": True}

    verifier = PubSubTokenVerifier(
        audience="https://agent.example.run.app/v1/events/pubsub",
        service_account_email="pubsub-push@example.iam.gserviceaccount.com",
        demo_mode=False,
        token_validator=validator,
    )
    assert verifier.verify("Bearer signed-token") is True
    assert calls == [("signed-token", "https://agent.example.run.app/v1/events/pubsub")]


def test_pubsub_token_verifier_rejects_wrong_identity() -> None:
    verifier = PubSubTokenVerifier(
        audience="https://agent.example.run.app/v1/events/pubsub",
        service_account_email="expected@example.iam.gserviceaccount.com",
        demo_mode=False,
        token_validator=lambda token, audience: {"email": "other@example.iam.gserviceaccount.com", "email_verified": True},
    )
    assert verifier.verify("Bearer signed-token") is False


def test_production_pubsub_endpoint_rejects_unsigned_push() -> None:
    settings = Settings(
        demo_mode=False,
        ai_enabled=False,
        service_signing_secret="test-secret",
        pubsub_push_audience="https://agent.example.run.app/v1/events/pubsub",
        pubsub_push_service_account="pubsub@example.iam.gserviceaccount.com",
        workspace_path=Path(__file__).resolve().parents[2] / "seed" / "demo_workspace.json",
    )
    client = TestClient(create_app(Services(settings=settings)))
    response = client.post("/v1/events/pubsub", json=envelope(work_event("production-event")))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
