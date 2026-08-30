from __future__ import annotations

from datetime import datetime, timezone

from .adapters.guard import GoogleModelArmorGuard, LocalPromptGuard
from .adapters.model import DeterministicDemoModel, GoogleADKModel
from .agent_registry import ExecutableAgentRegistry
from .action_dispatch import DisabledActionPublisher, GooglePubSubActionPublisher, NullActionPublisher
from .config import Settings
from .evidence import EvidenceRetriever
from .memory import DecisionMemoryStore
from .missions import MissionRuntime
from .meetings import MeetingService
from .meeting_delegations import MeetingDelegationService
from .orchestrator import Orchestrator
from .persistence import StateStore, build_state_store
from .policy import PolicyEngine
from .preferences import PreferenceMemory
from .rate_limit import RateLimiter
from .registry import DelegateDirectory
from .routing import OrganizationRouter
from .security import ContentSecurityScanner
from .usage import ModelUsageGuard
from .work_state import WorkStateProjector
from .workspace import Workspace


def default_now() -> datetime:
    # Seeded demo time keeps evidence freshness and delegated authority deterministic.
    return datetime(2026, 8, 27, 13, 10, tzinfo=timezone.utc).astimezone()


def wall_clock_now() -> datetime:
    """Return real time for operational limits that must expire in production."""
    return datetime.now(timezone.utc).astimezone()


class Services:
    def __init__(
        self,
        settings: Settings | None = None,
        now_fn=None,
        state_store: StateStore | None = None,
        operational_now_fn=None,
    ):
        self.settings = settings or Settings.from_env()
        explicit_now_fn = now_fn is not None
        now_fn = now_fn or (default_now if self.settings.demo_mode else wall_clock_now)
        self.now_fn = now_fn
        operational_now_fn = operational_now_fn or (now_fn if explicit_now_fn else wall_clock_now)
        self.state_store = state_store or build_state_store(self.settings)
        self.workspace = Workspace(self.settings.workspace_path, state_store=self.state_store)
        self.policy = PolicyEngine(self.workspace, now_fn)
        self.scanner = ContentSecurityScanner()
        self.retriever = EvidenceRetriever(self.workspace, self.policy, self.scanner)
        self.router = OrganizationRouter(self.workspace)
        # The seeded narrative clock keeps fixture evidence and delegated
        # authority deterministic. Memory expiry is an operational safety
        # boundary, so production must evaluate it against real wall time.
        self.memory = DecisionMemoryStore(self.workspace, operational_now_fn)
        self.registry = DelegateDirectory(self.workspace)
        self.work_state = WorkStateProjector(self.workspace)
        self.meetings = MeetingService(self.workspace, now_fn)
        self.rate_limiter = RateLimiter(self.settings, operational_now_fn)
        self.usage_guard = ModelUsageGuard(
            self.workspace,
            operational_now_fn,
            max_calls_per_query=self.settings.model_max_calls_per_query,
            max_input_tokens_per_query=self.settings.model_max_input_tokens_per_query,
            max_output_tokens_per_query=self.settings.model_max_output_tokens_per_query,
            max_calls_per_day=self.settings.model_max_calls_per_day,
            max_input_tokens_per_day=self.settings.model_max_input_tokens_per_day,
            max_output_tokens_per_day=self.settings.model_max_output_tokens_per_day,
        )
        prompt_guard = (
            GoogleModelArmorGuard(
                project_id=self.settings.google_cloud_project,
                location=self.settings.model_armor_location,
                template_id=self.settings.model_armor_template_id,
                fail_closed=self.settings.model_armor_fail_closed,
            )
            if self.settings.model_armor_enabled
            else LocalPromptGuard()
        )
        model = (
            DeterministicDemoModel()
            if self.settings.demo_mode
            else GoogleADKModel(
                model_name=self.settings.gemini_model,
                max_output_tokens=min(600, self.settings.model_max_output_tokens_per_query),
            )
        )
        self.executable_registry = ExecutableAgentRegistry(self.settings, self.now_fn)
        self.action_publisher = (
            NullActionPublisher() if self.settings.demo_mode else (
                GooglePubSubActionPublisher(
                project_id=self.settings.google_cloud_project,
                topic_id=self.settings.action_command_topic,
                ) if self.settings.google_cloud_project and self.settings.action_command_topic
                else DisabledActionPublisher()
            )
        )
        self.mission_runtime = MissionRuntime(
            workspace=self.workspace,
            registry=self.executable_registry,
            now_fn=self.now_fn,
            model_name=self.settings.gemini_model,
            demo_mode=self.settings.demo_mode,
            prompt_guard=prompt_guard,
            usage_guard=self.usage_guard,
            action_publisher=self.action_publisher,
            policy=self.policy,
            project_id=self.settings.google_cloud_project,
            agent_engine_location=self.settings.agent_engine_location,
            agent_engine_id=self.settings.agent_engine_id,
        )
        self.preference_memory = PreferenceMemory(
            project_id=self.settings.google_cloud_project,
            location=self.settings.agent_engine_location,
            agent_engine_id=self.settings.agent_engine_id,
            demo_mode=self.settings.demo_mode,
        )
        self.meetings.mission_runtime = self.mission_runtime
        # Demo fixtures use a stable narrative clock, while production Live
        # limits and resumption TTLs must advance with real wall time.
        live_now_fn = now_fn if self.settings.demo_mode else operational_now_fn
        self.meeting_delegations = MeetingDelegationService(
            self.workspace,
            self.policy,
            live_now_fn,
            self.settings,
            prompt_guard,
            handoff_model=model,
            usage_guard=self.usage_guard,
        )
        self.orchestrator = Orchestrator(
            workspace=self.workspace,
            model=model,
            policy=self.policy,
            retriever=self.retriever,
            router=self.router,
            memory=self.memory,
            now_fn=now_fn,
            ai_enabled=self.settings.ai_enabled,
            usage_guard=self.usage_guard,
            prompt_guard=prompt_guard,
        )
