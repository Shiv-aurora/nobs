from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.adapters.model import ModelAdapter, SynthesisResult
from app.config import Settings
from app.main import create_app
from app.models import Evidence, Intent
from app.service import Services
from app.usage import ModelUsage


class CountingModel(ModelAdapter):
    model_name = "counting-model"
    expected_calls = 1
    max_output_tokens = 20

    def __init__(self) -> None:
        self.calls = 0

    def synthesize(self, *, text: str, intent: Intent, evidence: list[Evidence]) -> SynthesisResult:
        self.calls += 1
        return SynthesisResult(
            text="SEC-184 remains the only launch gate.",
            usage=ModelUsage(model_name=self.model_name, calls=1, input_tokens=30, output_tokens=9),
        )


def make_services(**overrides) -> Services:
    values = {
        "demo_mode": True,
        "workspace_path": Path(__file__).resolve().parents[2] / "seed" / "demo_workspace.json",
        "max_user_per_minute": 50,
        "max_user_per_hour": 100,
        "max_user_per_day": 200,
        "max_org_per_minute": 100,
        "max_org_per_day": 500,
        "max_concurrent_runs": 2,
        "model_max_calls_per_query": 4,
        "model_max_input_tokens_per_query": 24_000,
        "model_max_output_tokens_per_query": 2_400,
        "model_max_calls_per_day": 200,
        "model_max_input_tokens_per_day": 1_000_000,
        "model_max_output_tokens_per_day": 100_000,
    }
    values.update(overrides)
    return Services(settings=Settings(**values))


def test_per_query_budget_blocks_before_model_execution() -> None:
    services = make_services(model_max_input_tokens_per_query=1)
    model = CountingModel()
    services.orchestrator.model = model
    client = TestClient(create_app(services))

    response = client.post("/v1/query", json={"requester_id": "maya", "text": "Why is Atlas blocked?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["headline"] == "AI budget guard active"
    assert model.calls == 0
    assert services.workspace.stats["model_budget_blocks"] == 1


def test_daily_call_budget_is_hard_and_usage_is_reconciled() -> None:
    services = make_services(model_max_calls_per_day=1)
    model = CountingModel()
    services.orchestrator.model = model
    client = TestClient(create_app(services))
    request = {"requester_id": "maya", "text": "Why is Atlas blocked?"}

    first = client.post("/v1/query", json=request).json()
    second = client.post("/v1/query", json=request).json()

    assert first["status"] == "answered"
    assert first["model_calls"] == 1
    assert first["model_input_tokens"] == 30
    assert second["headline"] == "AI budget guard active"
    assert model.calls == 1
    assert services.workspace.stats["model_calls"] == 1


def test_decision_memory_still_operates_when_model_budget_is_exhausted() -> None:
    services = make_services(model_max_calls_per_day=0)
    model = CountingModel()
    services.orchestrator.model = model
    client = TestClient(create_app(services))

    created = client.post(
        "/v1/query",
        json={"requester_id": "maya", "text": "Can we bypass security review for the $200K customer?"},
    ).json()
    assert created["status"] == "escalated"
    client.post(
        f"/v1/decisions/{created['decision_id']}/resolve",
        json={"actor_id": "alex", "status": "rejected", "rationale": "The control remains mandatory."},
    )
    repeated = client.post(
        "/v1/query",
        json={"requester_id": "maya", "text": "Can we make the Atlas security exception?"},
    ).json()
    assert repeated["status"] == "answered"
    assert repeated["cached"] is True
    assert model.calls == 0
