from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.service import Services


DEMO_NOW = datetime.fromisoformat("2026-08-27T13:10:00-04:00")


@pytest.fixture
def services() -> Services:
    settings = Settings(
        demo_mode=True,
        ai_enabled=True,
        service_signing_secret="test-secret",
        workspace_path=Path(__file__).resolve().parents[2] / "seed" / "demo_workspace.json",
        max_user_per_minute=50,
        max_user_per_hour=100,
        max_user_per_day=200,
        max_org_per_minute=100,
        max_org_per_day=500,
        max_concurrent_runs=2,
    )
    return Services(settings=settings, now_fn=lambda: DEMO_NOW)


@pytest.fixture
def client(services: Services) -> TestClient:
    return TestClient(create_app(services))
