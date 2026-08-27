from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import Evidence, User
from .workspace import Workspace


@dataclass(frozen=True)
class AuthorityResolution:
    assignee_id: str | None
    reason: str
    authority: str


class PolicyEngine:
    def __init__(self, workspace: Workspace, now_fn):
        self.workspace = workspace
        self.now_fn = now_fn

    def can_read(self, requester: User, evidence: Evidence) -> bool:
        if evidence.allowed_roles and not set(evidence.allowed_roles).intersection(requester.roles):
            return False
        if evidence.scope == "company":
            return True
        if evidence.scope == "hr":
            return "hr" in requester.roles
        if evidence.scope.startswith("project:"):
            project_id = evidence.scope.split(":", 1)[1]
            return project_id in requester.project_ids or "executive" in requester.roles
        if evidence.scope.startswith("team:"):
            team_id = evidence.scope.split(":", 1)[1]
            return team_id in requester.team_ids
        if evidence.scope.startswith("private:user:"):
            return evidence.scope.endswith(requester.id)
        return False

    def resolve_authority(self, authority: str, project_id: str | None = None) -> AuthorityResolution:
        now: datetime = self.now_fn()
        if authority == "atlas_security_approval":
            primary = self.workspace.users["sarah"]
            if primary.availability.status != "out_of_office":
                return AuthorityResolution(primary.id, "Sarah is the active Security Approver.", authority)
            for delegation in self.workspace.delegations.values():
                if (
                    delegation.authority == authority
                    and delegation.from_user_id == primary.id
                    and delegation.starts_at <= now <= delegation.ends_at
                ):
                    delegate = self.workspace.users[delegation.to_user_id]
                    if "acting_security_approver" in delegate.roles:
                        return AuthorityResolution(
                            delegate.id,
                            f"{primary.name} is out of office; valid delegated authority routes to {delegate.name}.",
                            authority,
                        )
            return AuthorityResolution(None, "No active Security Approver is available.", authority)
        return AuthorityResolution(None, "No authority rule matched.", authority)

    def actor_can_resolve(self, actor_id: str, authority: str) -> bool:
        resolution = self.resolve_authority(authority)
        return resolution.assignee_id == actor_id
