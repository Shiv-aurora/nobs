from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import uuid4


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "nobs_fields", {}))
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def event(logger: logging.Logger, message: str, *, level: int = logging.INFO, **fields: Any) -> None:
    logger.log(level, message, extra={"nobs_fields": fields})


@contextmanager
def executor_span(name: str, **attributes: Any):
    try:
        from opentelemetry import trace
    except ImportError:
        yield None
        return
    with trace.get_tracer("nobs.executor").start_as_current_span(name) as span:
        for key, value in attributes.items():
            if value not in (None, ""):
                span.set_attribute(f"nobs.{key}", value)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            raise


def configure_opentelemetry(app: Any, *, endpoint: str) -> bool:
    if not endpoint:
        return False
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    except ImportError:
        logging.getLogger(__name__).warning("OpenTelemetry endpoint configured but dependencies are unavailable")
        return False
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    provider = TracerProvider(resource=Resource.create({"service.name": "noping-action-executor"}))
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint, session=AuthorizedSession(credentials))))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz")
    return True


class RequestTelemetryMiddleware:
    def __init__(self, app: Callable[..., Any]):
        self.app = app
        self.logger = logging.getLogger("nobs.executor.http")

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = 500
        request_id = uuid4().hex

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status
            if message.get("type") == "http.response.start":
                status = int(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if scope.get("path") != "/healthz":
                event(
                    self.logger,
                    "http.request",
                    method=scope.get("method", ""),
                    path=scope.get("path", ""),
                    status_code=status,
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                    request_id=request_id,
                )
