from __future__ import annotations

import base64
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .calendar import GoogleCalendarAdapter
from .config import Settings
from .observability import RequestTelemetryMiddleware, configure_logging, configure_opentelemetry
from .service import ActionExecutor
from .store import FirestoreCommandStore


class PubSubMessage(BaseModel):
    data: str
    message_id: str = ""


class PubSubEnvelope(BaseModel):
    message: PubSubMessage


def build_executor(settings: Settings) -> ActionExecutor:
    store = FirestoreCommandStore(
        project_id=settings.project_id,
        database=settings.firestore_database,
        organization_id=settings.organization_id,
    )
    calendar = GoogleCalendarAdapter(settings.calendar_credentials_b64, settings.calendar_id)
    return ActionExecutor(settings, store, calendar)


def create_app(executor: ActionExecutor | None = None) -> FastAPI:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    app = FastAPI(title="NoBS Action Executor", version="0.1.0")
    app.state.executor = executor
    app.add_middleware(RequestTelemetryMiddleware)

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/commands/pubsub")
    def execute_command(envelope: PubSubEnvelope):
        try:
            payload = json.loads(base64.b64decode(envelope.message.data, validate=True))
            command_id = str(payload["command_id"])
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid command envelope") from exc
        runtime = app.state.executor or build_executor(Settings.from_env())
        try:
            return runtime.execute(command_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Command not found") from exc

    configure_opentelemetry(app, endpoint=settings.otel_endpoint)
    return app


app = create_app()
