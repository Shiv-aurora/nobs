from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from app import BudgetData, Settings, create_app, decode_budget_envelope, evaluate_budget


class FakeStopper:
    def __init__(self, status: str = "RUNNING"):
        self.current_status = status
        self.stop_calls = 0

    def status(self) -> str:
        return self.current_status

    def stop(self) -> None:
        self.stop_calls += 1


def settings(*, dry_run: bool = False) -> Settings:
    return Settings(
        project_id="demo-project",
        zone="us-central1-a",
        instance_name="noping-mattermost",
        expected_budget_name="NoPing $25 guardrail",
        trigger_ratio=0.90,
        dry_run=dry_run,
    )


def envelope(cost: float, budget: float = 25.0, name: str = "NoPing $25 guardrail") -> dict:
    payload = {
        "budgetDisplayName": name,
        "costAmount": cost,
        "budgetAmount": budget,
        "alertThresholdExceeded": 0.9 if cost >= 22.5 else None,
        "currencyCode": "USD",
    }
    return {"message": {"data": base64.b64encode(json.dumps(payload).encode()).decode()}}


def test_decode_budget_envelope() -> None:
    value = decode_budget_envelope(envelope(7.5))
    assert value.cost_amount == 7.5
    assert value.ratio == 0.3


def test_below_threshold_does_nothing() -> None:
    stopper = FakeStopper()
    result = evaluate_budget(BudgetData.model_validate({"budgetDisplayName": "NoPing $25 guardrail", "costAmount": 10, "budgetAmount": 25}), settings=settings(), stopper=stopper)
    assert result["action"] == "none"
    assert stopper.stop_calls == 0


def test_threshold_stops_running_instance() -> None:
    stopper = FakeStopper("RUNNING")
    result = evaluate_budget(
        BudgetData.model_validate({"budgetDisplayName": "NoPing $25 guardrail", "costAmount": 23, "budgetAmount": 25}),
        settings=settings(),
        stopper=stopper,
    )
    assert result["action"] == "stop_requested"
    assert stopper.stop_calls == 1


def test_duplicate_notification_is_idempotent() -> None:
    stopper = FakeStopper("TERMINATED")
    result = evaluate_budget(
        BudgetData.model_validate({"budgetDisplayName": "NoPing $25 guardrail", "costAmount": 24, "budgetAmount": 25}),
        settings=settings(),
        stopper=stopper,
    )
    assert result["action"] == "already_stopped"
    assert stopper.stop_calls == 0


def test_wrong_budget_is_ignored() -> None:
    stopper = FakeStopper()
    result = evaluate_budget(
        BudgetData.model_validate({"budgetDisplayName": "Another budget", "costAmount": 25, "budgetAmount": 25}),
        settings=settings(),
        stopper=stopper,
    )
    assert result["action"] == "ignored"


def test_dry_run_never_stops() -> None:
    stopper = FakeStopper()
    result = evaluate_budget(
        BudgetData.model_validate({"budgetDisplayName": "NoPing $25 guardrail", "costAmount": 25, "budgetAmount": 25}),
        settings=settings(dry_run=True),
        stopper=stopper,
    )
    assert result["action"] == "dry_run"
    assert stopper.stop_calls == 0


def test_http_endpoint() -> None:
    stopper = FakeStopper()
    client = TestClient(create_app(settings(), stopper))
    response = client.post("/", json=envelope(23))
    assert response.status_code == 200
    assert response.json()["action"] == "stop_requested"
    assert stopper.stop_calls == 1


def test_invalid_envelope_returns_400() -> None:
    client = TestClient(create_app(settings(), FakeStopper()))
    response = client.post("/", json={"message": {"data": "not-base64"}})
    assert response.status_code == 400
