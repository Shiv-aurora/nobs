from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth import SIGNATURE_VERSION, SignatureVerifier
from app.config import Settings
from app.main import create_app
from app.service import Services


def production_client() -> tuple[TestClient, SignatureVerifier]:
    settings = Settings(
        demo_mode=False,
        ai_enabled=False,
        service_signing_secret="test-secret",
        workspace_path=Path(__file__).resolve().parents[2] / "seed" / "demo_workspace.json",
        max_user_per_minute=50,
        max_user_per_hour=100,
        max_user_per_day=200,
        max_org_per_minute=100,
        max_org_per_day=500,
        max_concurrent_runs=2,
    )
    services = Services(settings=settings)
    return TestClient(create_app(services)), SignatureVerifier("test-secret", demo_mode=False)


def signed_headers(verifier: SignatureVerifier, method: str, target: str, body: bytes = b"", *, timestamp: str | None = None) -> dict[str, str]:
    timestamp = timestamp or str(int(time.time()))
    return {
        "X-NoPing-Timestamp": timestamp,
        "X-NoPing-Signature-Version": SIGNATURE_VERSION,
        "X-NoPing-Signature": verifier.sign(timestamp, method, target, body),
        "Content-Type": "application/json",
    }


def test_production_rejects_unsigned_request() -> None:
    client, _ = production_client()
    response = client.get("/v1/bootstrap?user_id=maya")
    assert response.status_code == 401


def test_production_accepts_signed_request() -> None:
    client, verifier = production_client()
    target = "/v1/bootstrap?user_id=maya"
    response = client.get(target, headers=signed_headers(verifier, "GET", target))
    assert response.status_code == 200
    assert response.json()["current_user"]["id"] == "maya"


def test_signature_cannot_be_replayed_on_another_target() -> None:
    client, verifier = production_client()
    headers = signed_headers(verifier, "GET", "/v1/registry")
    response = client.get("/v1/audit", headers=headers)
    assert response.status_code == 401


def test_expired_signature_is_rejected() -> None:
    client, verifier = production_client()
    target = "/healthz"
    timestamp = str(int(time.time()) - 1_000)
    response = client.get(target, headers=signed_headers(verifier, "GET", target, timestamp=timestamp))
    assert response.status_code == 401


def test_python_signature_matches_shared_contract() -> None:
    vector = json.loads((Path(__file__).resolve().parents[2] / "contracts" / "signature_vector.json").read_text())
    verifier = SignatureVerifier(vector["secret"], demo_mode=False)
    assert verifier.sign(vector["timestamp"], vector["method"], vector["target"], vector["body"].encode()) == vector["signature"]
