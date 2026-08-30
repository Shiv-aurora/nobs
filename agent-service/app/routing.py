from __future__ import annotations

import re
import time

from .models import DelegationResolution, DelegationResolutionRequest, Intent, RouteStep
from .workspace import Workspace


_ACTIONABLE = re.compile(
    r"(?:\?|^\s*(?:what|why|who|when|where|how|can|could|would|should|does|do|is|are|will|status|update)\b|\b(?:i|we)\s+need\b|\bplease\b|\bcan someone\b|\bcould someone\b|\bhelp\s+(?:me|us)\b)",
    re.I,
)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


class OrganizationRouter:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def resolve_delegation(self, request: DelegationResolutionRequest) -> DelegationResolution:
        """Decide whether an ordinary channel message belongs to a delegate's scope.

        This is intentionally deterministic and model-free. It runs for every human
        channel message, so it must not consume query/model budget or turn routine
        conversation into a wall of bot replies.
        """
        if request.requester_id not in self.workspace.users:
            return DelegationResolution(eligible=False, reason="Unknown organizational identity.", confidence=1.0)

        raw = request.text.strip()
        text = raw.lower()
        context = request.conversation_context
        channel_name = str(context.get("channel_name", "")).lower()
        channel_display_name = str(context.get("channel_display_name", "")).lower()
        channel_purpose = str(context.get("channel_purpose", "")).lower()
        channel_context = " ".join((channel_name, channel_display_name, channel_purpose))

        if "@noping" in text:
            return DelegationResolution(
                eligible=True,
                kind="organization",
                scope="organization",
                reason="The organization delegate was explicitly addressed.",
                confidence=1.0,
            )
        if not _ACTIONABLE.search(raw):
            return DelegationResolution(
                eligible=False,
                reason="The message is conversational or informational rather than an answerable work request.",
                confidence=0.92,
            )

        # A named employee is the represented subject even when another team
        # (for example People Operations) owns the policy being enforced. This
        # keeps "Sarah's salary" visibly answered by Sarah's delegate while the
        # deterministic HR boundary still refuses the underlying data request.
        named_users = []
        for user in self.workspace.users.values():
            aliases = {user.id.lower(), user.name.lower(), user.name.split()[0].lower()}
            if any(re.search(rf"\b{re.escape(alias)}(?:'s)?\b", text) for alias in aliases):
                if user.id != request.requester_id:
                    named_users.append(user)
        if len(named_users) == 1:
            user = named_users[0]
            return DelegationResolution(
                eligible=True,
                kind="personal",
                represented_user_id=user.id,
                represented_user_name=user.name,
                scope=f"user:{user.id}",
                reason=f"The request is about {user.name} and belongs to that employee delegate's boundary.",
                confidence=0.99,
            )
        if len(named_users) > 1:
            return DelegationResolution(
                eligible=True,
                kind="organization",
                scope="cross-functional",
                reason="The request names multiple employees and requires one coordinated route.",
                confidence=0.99,
            )

        combined = f"{text} {channel_context}"
        candidates: list[tuple[str, str, float]] = []

        # Specific work-item ownership outranks broader team/channel vocabulary.
        for item in self.workspace.work_items.values():
            item_terms = (item.id.lower(), item.key.lower(), item.title.lower())
            if _contains_any(text, item_terms):
                candidates.append((item.owner_user_id, f"work-item:{item.id}", 0.99))

        scope_rules = (
            (("sec-184", "security", "penetration", "risk", "approval", "vulnerability"), "sarah", "team:security"),
            (("auth-392", "engineering", "engineer", "ios", "mobile", "pull request", " pr ", "refresh token"), "daniel", "team:engineering"),
            (("roadmap", "product", "priority", "launch sequence", "release plan"), "priya", "team:product"),
            (("customer", "support", "northstar", "escalation"), "maya", "team:support"),
            (("people operations", "hr", "compensation", "salary"), "helen", "team:people"),
        )
        for terms, user_id, scope in scope_rules:
            if _contains_any(combined, terms):
                candidates.append((user_id, scope, 0.94))

        # Remove duplicates and never present the sender's own delegate as a proxy
        # in a shared channel; the organization route is clearer in that case.
        unique = {user_id: (scope, confidence) for user_id, scope, confidence in candidates if user_id != request.requester_id}
        if len(unique) == 1:
            user_id, (scope, confidence) = next(iter(unique.items()))
            user = self.workspace.users[user_id]
            return DelegationResolution(
                eligible=True,
                kind="personal",
                represented_user_id=user.id,
                represented_user_name=user.name,
                scope=scope,
                reason=f"The request maps to {user.name}'s active work scope.",
                confidence=confidence,
            )
        if len(unique) > 1:
            return DelegationResolution(
                eligible=True,
                kind="organization",
                scope="cross-functional",
                reason="The request spans multiple employee or team scopes.",
                confidence=0.95,
            )

        atlas_context = "atlas" in combined or "project-atlas" in channel_name
        if atlas_context:
            return DelegationResolution(
                eligible=True,
                kind="organization",
                scope="project:atlas",
                reason="The request belongs to the active Project Atlas workspace.",
                confidence=0.91,
            )

        return DelegationResolution(
            eligible=False,
            reason="No employee, project, or team scope matched with sufficient confidence.",
            confidence=0.84,
        )

    def build_route(self, requester_id: str, text: str, intent: Intent, delegate_for_user_id: str | None = None) -> list[RouteStep]:
        represented = self.workspace.users.get(delegate_for_user_id or "")
        route_started = time.perf_counter()
        project = self.workspace.projects["atlas"]
        route = [RouteStep(
            ordinal=1,
            delegate_id=f"delegate:project:{project.id}",
            delegate_name=f"{project.name} Delegate",
            reason="Atlas is the named project and owns the launch state.",
            outcome="Project scope selected for permission-filtered evidence retrieval.",
            duration_ms=round((time.perf_counter() - route_started) * 1000, 3),
        )]
        if intent in {Intent.FACTUAL, Intent.LIVE_STATUS}:
            step_started = time.perf_counter()
            personal = represented or self.workspace.users["sarah"]
            route.extend([
                RouteStep(
                    ordinal=2,
                    delegate_id="delegate:team:engineering",
                    delegate_name="Engineering Delegate",
                    reason="AUTH-392 is an engineering dependency linked to Atlas.",
                    outcome="Engineering scope selected for permission-filtered evidence retrieval.",
                    duration_ms=round((time.perf_counter() - step_started) * 1000, 3),
                ),
                RouteStep(
                    ordinal=3,
                    delegate_id=f"delegate:user:{personal.id}",
                    delegate_name=f"{personal.name} Delegate",
                    reason=f"{personal.name}'s working context owns or informs the active launch gate.",
                    outcome="Permission-aware personal scope selected without interrupting the employee.",
                    duration_ms=round((time.perf_counter() - step_started) * 1000, 3),
                ),
                RouteStep(
                    ordinal=4,
                    delegate_id="delegate:team:security",
                    delegate_name="Security Delegate",
                    reason="SEC-184 is the active launch gate.",
                    outcome="Security scope selected for permission-filtered evidence retrieval.",
                    duration_ms=round((time.perf_counter() - step_started) * 1000, 3),
                ),
            ])
        elif intent in {Intent.POLICY, Intent.DECISION}:
            step_started = time.perf_counter()
            personal = represented or self.workspace.users["sarah"]
            route.extend([
                RouteStep(
                    ordinal=2,
                    delegate_id="delegate:policy:sec-pol-12",
                    delegate_name="SEC-POL-12 Policy Delegate",
                    reason="The request could alter a mandatory launch control.",
                    outcome="Security policy scope selected for deterministic evaluation.",
                    duration_ms=round((time.perf_counter() - step_started) * 1000, 3),
                ),
                RouteStep(
                    ordinal=3,
                    delegate_id=f"delegate:user:{personal.id}",
                    delegate_name=f"{personal.name} Delegate",
                    reason="The security owner context establishes current availability and delegated authority.",
                    outcome="Security-owner scope selected for permission-filtered availability evidence.",
                    duration_ms=round((time.perf_counter() - step_started) * 1000, 3),
                ),
                RouteStep(
                    ordinal=4,
                    delegate_id="delegate:authority",
                    delegate_name="Authority Gate",
                    reason="Only a valid human approver may decide the exception.",
                    outcome="Authority policy selected; validation runs after evidence retrieval.",
                    step_type="deterministic_policy",
                    duration_ms=round((time.perf_counter() - step_started) * 1000, 3),
                ),
            ])
        for ordinal, step in enumerate(route, start=1):
            step.ordinal = ordinal
        return route[:4]
