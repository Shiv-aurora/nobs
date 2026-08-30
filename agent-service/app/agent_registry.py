from __future__ import annotations

import os
import logging

from .config import Settings
from .mission_models import AgentManifest, ExecutableRegistryResponse


logger = logging.getLogger(__name__)


class ExecutableAgentRegistry:
    """Versioned manifests for code that can actually execute in a mission.

    Google Agent Registry is the preferred discovery plane. These local
    manifests remain the enforceable fallback and are persisted with every run,
    so routing never depends on a marketing label or a mutable display name.
    """

    def __init__(self, settings: Settings, now_fn):
        self.settings = settings
        self.now_fn = now_fn
        self._manifests = {item.id: item for item in self._build()}
        self._native_services: set[str] = set()
        self._native_error = "Native discovery is disabled."
        if settings.agent_registry_enabled:
            self._discover_native_services()

    SERVICE_IDS = {
        "agent:meeting-mission-controller": "nobs-meeting-mission-controller-v1",
        "agent:work-graph-specialist": "nobs-work-graph-specialist-v1",
        "agent:policy-evidence-specialist": "nobs-policy-evidence-specialist-v1",
        "agent:meeting-resolution-synthesizer": "nobs-meeting-resolution-synthesizer-v1",
    }

    def _discover_native_services(self) -> None:
        try:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"])
            url = (
                "https://agentregistry.googleapis.com/v1/projects/"
                f"{self.settings.google_cloud_project}/locations/{self.settings.agent_registry_location}/services"
            )
            response = AuthorizedSession(credentials).get(url, timeout=8)
            response.raise_for_status()
            services = response.json().get("services", [])
            self._native_services = {str(item.get("name", "")).rsplit("/", 1)[-1] for item in services}
            missing = set(self.SERVICE_IDS.values()) - self._native_services
            self._native_error = (
                "All versioned executable agents discovered in Google Agent Registry."
                if not missing else f"Missing native registrations: {', '.join(sorted(missing))}"
            )
        except Exception as exc:  # pragma: no cover - deployment-only failure path
            self._native_error = f"Google Agent Registry discovery failed: {type(exc).__name__}"
            logger.warning(self._native_error)

    def _build(self) -> list[AgentManifest]:
        runtime = "deterministic_test_program" if self.settings.demo_mode else "google_adk_llm"
        revision = os.getenv("K_REVISION", self.settings.version)
        identity = os.getenv(
            "NOPING_RUNTIME_IDENTITY",
            f"noping-agent@{self.settings.google_cloud_project}.iam.gserviceaccount.com"
            if self.settings.google_cloud_project else "local-test-runtime",
        )
        registered_at = self.now_fn()
        common = {
            "version": "1.0.0",
            "owner": "NoBS Platform",
            "runtime": runtime,
            "deployment_target": os.getenv("K_SERVICE", "noping-agent-service"),
            "deployment_revision": revision,
            "model": None if self.settings.demo_mode else self.settings.gemini_model,
            "runtime_identity": identity,
            "registered_at": registered_at,
        }
        return [
            AgentManifest(
                id="agent:meeting-mission-controller",
                name="Meeting Mission Controller",
                input_schema="MeetingMissionInput@1",
                output_schema="MissionPlan@1",
                capabilities=["agenda_decomposition", "specialist_routing", "mission_resume"],
                tools=["executable_agent_registry", "mission_state_store"],
                allowed_scopes=["meeting:metadata", "meeting:agenda", "agent:manifests"],
                **common,
            ),
            AgentManifest(
                id="agent:work-graph-specialist",
                name="Work Graph Specialist",
                input_schema="WorkGraphInput@1",
                output_schema="SpecialistReport@1",
                capabilities=["work_state_retrieval", "dependency_mapping", "evidence_citation"],
                tools=["semantic_work_state", "evidence_retriever"],
                allowed_scopes=["project:*", "team:*", "work_item:*"],
                **common,
            ),
            AgentManifest(
                id="agent:policy-evidence-specialist",
                name="Policy Evidence Specialist",
                input_schema="PolicyEvidenceInput@1",
                output_schema="SpecialistReport@1",
                capabilities=["policy_retrieval", "authority_boundary_detection", "evidence_citation"],
                tools=["policy_engine", "evidence_retriever"],
                allowed_scopes=["policy:*", "delegation:*", "meeting:agenda"],
                **common,
            ),
            AgentManifest(
                id="agent:meeting-resolution-synthesizer",
                name="Meeting Resolution Synthesizer",
                input_schema="ValidatedMissionEvidence@1",
                output_schema="MeetingResolution@1",
                capabilities=["agenda_resolution", "meeting_recommendation", "command_proposal"],
                tools=["validated_claim_reader"],
                allowed_scopes=["mission:validated_claims", "meeting:agenda"],
                **common,
            ),
        ]

    def get(self, agent_id: str) -> AgentManifest:
        manifest = self._manifests.get(agent_id)
        if not manifest or not manifest.approved or manifest.health != "ready":
            raise LookupError(f"Executable agent is not approved and ready: {agent_id}")
        return manifest

    def get_by_service_id(self, service_id: str) -> AgentManifest:
        agent_id = next((agent for agent, native in self.SERVICE_IDS.items() if native == service_id), None)
        if not agent_id:
            raise LookupError(service_id)
        return self.get(agent_id)

    def list(self) -> list[AgentManifest]:
        return list(self._manifests.values())

    def response(self) -> ExecutableRegistryResponse:
        complete = set(self.SERVICE_IDS.values()).issubset(self._native_services)
        return ExecutableRegistryResponse(
            agents=self.list(),
            source="google_agent_registry" if complete else "local_manifest",
            source_detail=self._native_error,
        )
