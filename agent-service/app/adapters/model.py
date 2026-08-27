from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Evidence, Intent


class ModelAdapter(ABC):
    @abstractmethod
    def synthesize(self, *, text: str, intent: Intent, evidence: list[Evidence]) -> str:
        raise NotImplementedError


class DeterministicDemoModel(ModelAdapter):
    """Deterministic demo behavior. Production swaps this for the Google ADK/Gemini adapter."""

    def synthesize(self, *, text: str, intent: Intent, evidence: list[Evidence]) -> str:
        lowered = text.lower()
        if intent == Intent.LIVE_STATUS:
            return (
                "Daniel Kim is handling AUTH-392; his fix is in PR #892, all 84 checks passed, "
                "and it is awaiting one reviewer. Sarah Chen is out through 9:00 AM tomorrow, "
                "so Alex Morgan is the authorized security approver tonight."
            )
        if intent == Intent.POLICY:
            return "SEC-POL-12 requires an active Security Approver before any P0 production launch. Revenue urgency does not waive the control."
        if "vendor" in lowered or "attachment" in lowered:
            return "The trusted Atlas evidence still shows SEC-184 as the launch gate. One untrusted attachment was blocked and excluded from the answer."
        return (
            "Project Atlas has not shipped because SEC-184, the final penetration-test review, "
            "is still pending. Engineering completed the required auth change and PR #892 passed "
            "its checks; security review is the only remaining launch gate."
        )


class GoogleADKModel(ModelAdapter):
    """Production port. Codex wires google-adk and Gemini 3.5+ without changing orchestration."""

    def __init__(self, model_name: str = "gemini-3.5-flash"):
        self.model_name = model_name

    def synthesize(self, *, text: str, intent: Intent, evidence: list[Evidence]) -> str:
        raise RuntimeError("Google ADK adapter is not configured in Phase 1. Set NOPING_DEMO_MODE=true or complete the Codex handoff.")
