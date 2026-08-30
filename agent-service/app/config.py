from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    demo_mode: bool = True
    ai_enabled: bool = True
    service_signing_secret: str = "dev-only-secret"
    persistence_backend: str = "memory"
    google_cloud_project: str = ""
    firestore_database: str = "(default)"
    organization_id: str = "acme"
    pubsub_push_audience: str = ""
    pubsub_push_service_account: str = ""
    gemini_model: str = "gemini-2.5-flash"
    live_model: str = "gemini-live-2.5-flash-native-audio"
    live_location: str = "us-central1"
    live_max_concurrent_sessions: int = 1
    live_max_session_minutes: int = 15
    live_max_org_minutes_per_day: int = 60
    live_max_tool_calls_per_session: int = 24
    live_max_reconnect_attempts: int = 5
    model_max_calls_per_query: int = 4
    model_max_input_tokens_per_query: int = 24_000
    model_max_output_tokens_per_query: int = 2_400
    model_max_calls_per_day: int = 200
    model_max_input_tokens_per_day: int = 1_000_000
    model_max_output_tokens_per_day: int = 100_000
    workspace_path: Path = Path(__file__).resolve().parents[2] / "seed" / "demo_workspace.json"
    max_user_per_minute: int = 6
    max_user_per_hour: int = 40
    max_user_per_day: int = 80
    max_org_per_minute: int = 20
    max_org_per_day: int = 200
    max_concurrent_runs: int = 2
    version: str = "0.1.0"
    log_level: str = "INFO"
    service_name: str = "noping-agent-service"
    otel_exporter_otlp_endpoint: str = ""
    model_armor_enabled: bool = False
    model_armor_location: str = "us-central1"
    model_armor_template_id: str = "noping-enterprise-guard"
    model_armor_fail_closed: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        def flag(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            return default if raw is None else raw.lower() in {"1", "true", "yes", "on"}

        return cls(
            demo_mode=flag("NOPING_DEMO_MODE", True),
            ai_enabled=flag("NOPING_AI_ENABLED", True),
            service_signing_secret=os.getenv("NOPING_SERVICE_SIGNING_SECRET", "dev-only-secret"),
            persistence_backend=os.getenv("NOPING_PERSISTENCE_BACKEND", "memory"),
            google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
            firestore_database=os.getenv("NOPING_FIRESTORE_DATABASE", "(default)"),
            organization_id=os.getenv("NOPING_ORGANIZATION_ID", "acme"),
            pubsub_push_audience=os.getenv("NOPING_PUBSUB_PUSH_AUDIENCE", ""),
            pubsub_push_service_account=os.getenv("NOPING_PUBSUB_PUSH_SERVICE_ACCOUNT", ""),
            gemini_model=os.getenv("NOPING_GEMINI_MODEL", "gemini-2.5-flash"),
            live_model=os.getenv("NOPING_LIVE_MODEL", "gemini-live-2.5-flash-native-audio"),
            live_location=os.getenv("NOPING_LIVE_LOCATION", "us-central1"),
            live_max_concurrent_sessions=int(os.getenv("NOPING_LIVE_MAX_CONCURRENT_SESSIONS", "1")),
            live_max_session_minutes=int(os.getenv("NOPING_LIVE_MAX_SESSION_MINUTES", "15")),
            live_max_org_minutes_per_day=int(os.getenv("NOPING_LIVE_MAX_ORG_MINUTES_PER_DAY", "60")),
            live_max_tool_calls_per_session=int(os.getenv("NOPING_LIVE_MAX_TOOL_CALLS_PER_SESSION", "24")),
            live_max_reconnect_attempts=int(os.getenv("NOPING_LIVE_MAX_RECONNECT_ATTEMPTS", "5")),
            model_max_calls_per_query=int(os.getenv("NOPING_MODEL_MAX_CALLS_PER_QUERY", "4")),
            model_max_input_tokens_per_query=int(os.getenv("NOPING_MODEL_MAX_INPUT_TOKENS_PER_QUERY", "24000")),
            model_max_output_tokens_per_query=int(os.getenv("NOPING_MODEL_MAX_OUTPUT_TOKENS_PER_QUERY", "2400")),
            model_max_calls_per_day=int(os.getenv("NOPING_MODEL_MAX_CALLS_PER_DAY", "200")),
            model_max_input_tokens_per_day=int(os.getenv("NOPING_MODEL_MAX_INPUT_TOKENS_PER_DAY", "1000000")),
            model_max_output_tokens_per_day=int(os.getenv("NOPING_MODEL_MAX_OUTPUT_TOKENS_PER_DAY", "100000")),
            workspace_path=Path(os.getenv("NOPING_WORKSPACE_PATH", str(cls.workspace_path))),
            max_user_per_minute=int(os.getenv("NOPING_MAX_USER_PER_MINUTE", "6")),
            max_user_per_hour=int(os.getenv("NOPING_MAX_USER_PER_HOUR", "40")),
            max_user_per_day=int(os.getenv("NOPING_MAX_USER_PER_DAY", "80")),
            max_org_per_minute=int(os.getenv("NOPING_MAX_ORG_PER_MINUTE", "20")),
            max_org_per_day=int(os.getenv("NOPING_MAX_ORG_PER_DAY", "200")),
            max_concurrent_runs=int(os.getenv("NOPING_MAX_CONCURRENT_RUNS", "2")),
            version=os.getenv("NOPING_VERSION", "0.1.0"),
            log_level=os.getenv("NOPING_LOG_LEVEL", "INFO"),
            service_name=os.getenv("OTEL_SERVICE_NAME", "noping-agent-service"),
            otel_exporter_otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", ""),
            model_armor_enabled=flag("NOPING_MODEL_ARMOR_ENABLED", False),
            model_armor_location=os.getenv("NOPING_MODEL_ARMOR_LOCATION", "us-central1"),
            model_armor_template_id=os.getenv("NOPING_MODEL_ARMOR_TEMPLATE_ID", "noping-enterprise-guard"),
            model_armor_fail_closed=flag("NOPING_MODEL_ARMOR_FAIL_CLOSED", True),
        )
