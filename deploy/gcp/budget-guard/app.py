from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
logger = logging.getLogger("noping.budget_guard")


@dataclass(frozen=True)
class Settings:
    project_id: str
    zone: str
    instance_name: str
    expected_budget_name: str
    trigger_ratio: float = 0.90
    dry_run: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        def flag(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}

        settings = cls(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT", "").strip(),
            zone=os.getenv("BUDGET_GUARD_ZONE", "").strip(),
            instance_name=os.getenv("BUDGET_GUARD_INSTANCE", "").strip(),
            expected_budget_name=os.getenv("BUDGET_GUARD_EXPECTED_BUDGET", "").strip(),
            trigger_ratio=float(os.getenv("BUDGET_GUARD_TRIGGER_RATIO", "0.90")),
            dry_run=flag("BUDGET_GUARD_DRY_RUN", False),
        )
        if not settings.project_id or not settings.zone or not settings.instance_name:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT, BUDGET_GUARD_ZONE, and BUDGET_GUARD_INSTANCE are required")
        if not 0.0 < settings.trigger_ratio <= 1.0:
            raise RuntimeError("BUDGET_GUARD_TRIGGER_RATIO must be in (0, 1]")
        return settings


class BudgetData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    budget_display_name: str = Field(default="", alias="budgetDisplayName")
    cost_amount: float = Field(alias="costAmount")
    budget_amount: float = Field(alias="budgetAmount")
    alert_threshold_exceeded: float | None = Field(default=None, alias="alertThresholdExceeded")
    currency_code: str = Field(default="USD", alias="currencyCode")

    @property
    def ratio(self) -> float:
        if self.budget_amount <= 0:
            return 0.0
        return self.cost_amount / self.budget_amount


class InstanceStopper(Protocol):
    def status(self) -> str: ...
    def stop(self) -> None: ...


class ComputeRESTStopper:
    METADATA_TOKEN_URL = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"

    def __init__(self, settings: Settings):
        self.settings = settings

    def _token(self) -> str:
        request = urllib.request.Request(self.METADATA_TOKEN_URL, headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        token = str(payload.get("access_token", ""))
        if not token:
            raise RuntimeError("metadata server returned no access token")
        return token

    def _request(self, method: str, suffix: str) -> dict[str, Any]:
        url = (
            "https://compute.googleapis.com/compute/v1/projects/"
            f"{self.settings.project_id}/zones/{self.settings.zone}/instances/"
            f"{self.settings.instance_name}{suffix}"
        )
        request = urllib.request.Request(
            url,
            method=method,
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Compute API {exc.code}: {detail[:300]}") from exc
        return json.loads(body.decode("utf-8")) if body else {}

    def status(self) -> str:
        payload = self._request("GET", "")
        return str(payload.get("status", "UNKNOWN"))

    def stop(self) -> None:
        self._request("POST", "/stop")


def decode_budget_envelope(payload: dict[str, Any]) -> BudgetData:
    try:
        encoded = payload["message"]["data"]
        decoded = base64.b64decode(encoded, validate=True)
        document = json.loads(decoded.decode("utf-8"))
        return BudgetData.model_validate(document)
    except Exception as exc:
        raise ValueError("invalid Cloud Billing Pub/Sub envelope") from exc


def evaluate_budget(
    budget: BudgetData,
    *,
    settings: Settings,
    stopper: InstanceStopper,
) -> dict[str, Any]:
    if settings.expected_budget_name and budget.budget_display_name != settings.expected_budget_name:
        return {"action": "ignored", "reason": "unexpected_budget", "ratio": budget.ratio}

    ratio = max(budget.ratio, budget.alert_threshold_exceeded or 0.0)
    if ratio < settings.trigger_ratio:
        return {"action": "none", "reason": "below_threshold", "ratio": ratio}

    current_status = stopper.status()
    if current_status in {"STOPPING", "TERMINATED"}:
        return {"action": "already_stopped", "status": current_status, "ratio": ratio}

    if settings.dry_run:
        return {"action": "dry_run", "status": current_status, "ratio": ratio}

    stopper.stop()
    return {"action": "stop_requested", "status": current_status, "ratio": ratio}


def create_app(settings: Settings | None = None, stopper: InstanceStopper | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()
    active_stopper = stopper or ComputeRESTStopper(active_settings)
    app = FastAPI(title="NoPing Budget Guard", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/")
    async def budget_notification(request: Request) -> dict[str, Any]:
        try:
            envelope = await request.json()
            budget = decode_budget_envelope(envelope)
            result = evaluate_budget(budget, settings=active_settings, stopper=active_stopper)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("budget_guard.error")
            raise HTTPException(status_code=500, detail="budget guard failed closed") from exc

        logger.info(
            json.dumps(
                {
                    "severity": "WARNING" if result["action"] in {"stop_requested", "dry_run"} else "INFO",
                    "message": "budget_guard.evaluated",
                    "budget": budget.budget_display_name,
                    "cost_amount": budget.cost_amount,
                    "budget_amount": budget.budget_amount,
                    "currency": budget.currency_code,
                    **result,
                },
                separators=(",", ":"),
            )
        )
        return result

    return app

