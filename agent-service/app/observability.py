from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import uuid4


_REDACTED_KEYS = {
    "authorization",
    "cookie",
    "evidence",
    "prompt",
    "query",
    "secret",
    "service_signing_secret",
    "text",
}


class JsonFormatter(logging.Formatter):
    """Cloud Logging-compatible JSON without adding a network logging dependency."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        fields = getattr(record, "noping_fields", {})
        if isinstance(fields, dict):
            for key, value in fields.items():
                if key.lower() in _REDACTED_KEYS:
                    payload[key] = "[REDACTED]"
                else:
                    payload[key] = value
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
        trace = getattr(record, "trace", "")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        if trace and project_id:
            payload["logging.googleapis.com/trace"] = f"projects/{project_id}/traces/{trace}"
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    for noisy in ("uvicorn.access", "httpcore", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def event(logger: logging.Logger, message: str, *, level: int = logging.INFO, **fields: Any) -> None:
    logger.log(level, message, extra={"noping_fields": fields})


def configure_opentelemetry(app: Any, *, service_name: str, endpoint: str) -> bool:
    """Enable vendor-neutral OTLP export when an endpoint is explicitly configured."""
    if not endpoint:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logging.getLogger(__name__).warning("OpenTelemetry endpoint configured but optional packages are unavailable")
        return False

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz")
    return True


class RequestTelemetryMiddleware:
    """Minimal ASGI request telemetry; never records request or response bodies."""

    def __init__(self, app: Callable[..., Any]):
        self.app = app
        self.logger = logging.getLogger("noping.http")

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        started = time.perf_counter()
        status_code = 500
        request_id = ""
        for key, value in scope.get("headers", []):
            if key.lower() == b"x-cloud-trace-context":
                request_id = value.decode(errors="ignore").split("/", 1)[0]
                break
            if key.lower() == b"x-request-id":
                request_id = value.decode(errors="ignore")
        request_id = request_id or uuid4().hex

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 500))
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if path != "/healthz":
                event(
                    self.logger,
                    "http.request",
                    method=scope.get("method", ""),
                    path=path,
                    status_code=status_code,
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                    request_id=request_id,
                )
