from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.service import Services


def test_per_user_minute_limit_returns_429():
    settings = Settings(
        demo_mode=True,
        workspace_path=Path(__file__).resolve().parents[2] / "seed" / "demo_workspace.json",
        max_user_per_minute=2,
        max_user_per_hour=20,
        max_user_per_day=20,
        max_org_per_minute=10,
        max_org_per_day=60,
        max_concurrent_runs=2,
    )
    services = Services(settings=settings)
    client = TestClient(create_app(services))
    payload = {"requester_id": "maya", "text": "Why is Atlas blocked?"}

    assert client.post("/v1/query", json=payload).status_code == 200
    assert client.post("/v1/query", json=payload).status_code == 200
    limited = client.post("/v1/query", json=payload)
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"


def test_demo_reset_clears_rate_limit_counters():
    settings = Settings(
        demo_mode=True,
        workspace_path=Path(__file__).resolve().parents[2] / "seed" / "demo_workspace.json",
        max_user_per_minute=1,
        max_user_per_hour=1,
        max_user_per_day=1,
        max_org_per_minute=1,
        max_org_per_day=1,
        max_concurrent_runs=1,
    )
    services = Services(settings=settings)
    client = TestClient(create_app(services))
    payload = {"requester_id": "maya", "text": "Why is Atlas blocked?"}

    assert client.post("/v1/query", json=payload).status_code == 200
    assert client.post("/v1/query", json=payload).status_code == 429
    assert client.post("/v1/demo/reset", json={}).status_code == 200
    assert client.post("/v1/query", json=payload).status_code == 200
