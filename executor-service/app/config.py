from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    project_id: str
    organization_id: str = "acme"
    firestore_database: str = "(default)"
    calendar_credentials_b64: str = ""
    calendar_id: str = "primary"
    lease_seconds: int = 60
    max_attempts: int = 3
    log_level: str = "INFO"
    otel_endpoint: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
            organization_id=os.getenv("NOPING_ORGANIZATION_ID", "acme"),
            firestore_database=os.getenv("NOPING_FIRESTORE_DATABASE", "(default)"),
            calendar_credentials_b64=os.getenv("NOPING_GOOGLE_CALENDAR_CREDENTIALS", ""),
            calendar_id=os.getenv("NOPING_GOOGLE_CALENDAR_ID", "primary"),
            lease_seconds=int(os.getenv("NOPING_EXECUTOR_LEASE_SECONDS", "60")),
            max_attempts=int(os.getenv("NOPING_EXECUTOR_MAX_ATTEMPTS", "3")),
            log_level=os.getenv("NOPING_LOG_LEVEL", "INFO"),
            otel_endpoint=os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", ""),
        )
