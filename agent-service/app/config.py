from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    demo_mode: bool = True
    ai_enabled: bool = True
    service_signing_secret: str = "dev-only-secret"
    workspace_path: Path = Path(__file__).resolve().parents[2] / "seed" / "demo_workspace.json"
    max_user_per_minute: int = 3
    max_user_per_hour: int = 20
    max_user_per_day: int = 20
    max_org_per_minute: int = 10
    max_org_per_day: int = 60
    max_concurrent_runs: int = 2
    version: str = "0.1.0"

    @classmethod
    def from_env(cls) -> "Settings":
        def flag(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            return default if raw is None else raw.lower() in {"1", "true", "yes", "on"}

        return cls(
            demo_mode=flag("NOPING_DEMO_MODE", True),
            ai_enabled=flag("NOPING_AI_ENABLED", True),
            service_signing_secret=os.getenv("NOPING_SERVICE_SIGNING_SECRET", "dev-only-secret"),
            workspace_path=Path(os.getenv("NOPING_WORKSPACE_PATH", str(cls.workspace_path))),
            max_user_per_minute=int(os.getenv("NOPING_MAX_USER_PER_MINUTE", "3")),
            max_user_per_hour=int(os.getenv("NOPING_MAX_USER_PER_HOUR", "20")),
            max_user_per_day=int(os.getenv("NOPING_MAX_USER_PER_DAY", "20")),
            max_org_per_minute=int(os.getenv("NOPING_MAX_ORG_PER_MINUTE", "10")),
            max_org_per_day=int(os.getenv("NOPING_MAX_ORG_PER_DAY", "60")),
            max_concurrent_runs=int(os.getenv("NOPING_MAX_CONCURRENT_RUNS", "2")),
            version=os.getenv("NOPING_VERSION", "0.1.0"),
        )
