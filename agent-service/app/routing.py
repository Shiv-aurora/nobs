from __future__ import annotations

from .models import Intent, RouteStep
from .workspace import Workspace


class OrganizationRouter:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def build_route(self, requester_id: str, text: str, intent: Intent) -> list[RouteStep]:
        requester = self.workspace.users[requester_id]
        route = [
            RouteStep(
                ordinal=1,
                delegate_id=f"delegate:user:{requester.id}",
                delegate_name=f"{requester.name} Delegate",
                reason="Receives the request with the requester's identity and permissions.",
                outcome="Intent and access context established.",
                duration_ms=42,
            ),
            RouteStep(
                ordinal=2,
                delegate_id="delegate:project:atlas",
                delegate_name="Project Atlas Delegate",
                reason="Atlas is the named project and owns the launch state.",
                outcome="Current blocker SEC-184 discovered.",
                duration_ms=67,
            ),
        ]
        if intent in {Intent.FACTUAL, Intent.LIVE_STATUS}:
            route.extend([
                RouteStep(
                    ordinal=3,
                    delegate_id="delegate:team:engineering",
                    delegate_name="Engineering Delegate",
                    reason="AUTH-392 is an engineering dependency linked to Atlas.",
                    outcome="PR #892 and Daniel's work state retrieved.",
                    duration_ms=58,
                ),
                RouteStep(
                    ordinal=4,
                    delegate_id="delegate:team:security",
                    delegate_name="Security Delegate",
                    reason="SEC-184 is the active launch gate.",
                    outcome="Review schedule and approver availability retrieved.",
                    duration_ms=61,
                ),
            ])
        elif intent in {Intent.POLICY, Intent.DECISION}:
            route.extend([
                RouteStep(
                    ordinal=3,
                    delegate_id="delegate:policy:sec-pol-12",
                    delegate_name="SEC-POL-12 Policy Delegate",
                    reason="The request could alter a mandatory launch control.",
                    outcome="Security approval requirement confirmed.",
                    duration_ms=49,
                ),
                RouteStep(
                    ordinal=4,
                    delegate_id="delegate:authority",
                    delegate_name="Authority Gate",
                    reason="Only a valid human approver may decide the exception.",
                    outcome="Sarah is unavailable; Alex's delegated authority validated.",
                    duration_ms=54,
                ),
            ])
        return route[:5]
