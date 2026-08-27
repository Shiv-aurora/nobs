from __future__ import annotations

from datetime import datetime, timezone

from .adapters.model import DeterministicDemoModel, GoogleADKModel
from .config import Settings
from .evidence import EvidenceRetriever
from .memory import DecisionMemoryStore
from .orchestrator import Orchestrator
from .persistence import StateStore, build_state_store
from .policy import PolicyEngine
from .rate_limit import RateLimiter
from .registry import DelegateRegistry
from .routing import OrganizationRouter
from .security import ContentSecurityScanner
from .work_state import WorkStateProjector
from .workspace import Workspace


def default_now() -> datetime:
    # Seeded demo time keeps evidence freshness and delegated authority deterministic.
    return datetime(2026, 8, 27, 13, 10, tzinfo=timezone.utc).astimezone()


class Services:
    def __init__(self, settings: Settings | None = None, now_fn=default_now, state_store: StateStore | None = None):
        self.settings = settings or Settings.from_env()
        self.now_fn = now_fn
        self.state_store = state_store or build_state_store(self.settings)
        self.workspace = Workspace(self.settings.workspace_path, state_store=self.state_store)
        self.policy = PolicyEngine(self.workspace, now_fn)
        self.scanner = ContentSecurityScanner()
        self.retriever = EvidenceRetriever(self.workspace, self.policy, self.scanner)
        self.router = OrganizationRouter(self.workspace)
        self.memory = DecisionMemoryStore(self.workspace, now_fn)
        self.registry = DelegateRegistry(self.workspace)
        self.work_state = WorkStateProjector(self.workspace)
        self.rate_limiter = RateLimiter(self.settings, now_fn)
        model = DeterministicDemoModel() if self.settings.demo_mode else GoogleADKModel()
        self.orchestrator = Orchestrator(
            workspace=self.workspace,
            model=model,
            policy=self.policy,
            retriever=self.retriever,
            router=self.router,
            memory=self.memory,
            now_fn=now_fn,
            ai_enabled=self.settings.ai_enabled,
        )
