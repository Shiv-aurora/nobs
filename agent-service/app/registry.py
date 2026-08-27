from __future__ import annotations

from .models import Delegate, RegistryResponse
from .workspace import Workspace


class DelegateRegistry:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def delegates(self) -> list[Delegate]:
        delegates: list[Delegate] = [
            Delegate(
                id="delegate:router",
                name="Organization Router",
                kind="router",
                entity_id="acme",
                capabilities=["entity_resolution", "delegate_selection", "route_budget_enforcement"],
                data_scopes=["directory", "organization_graph"],
            ),
            Delegate(
                id="delegate:authority",
                name="Authority Gate",
                kind="authority",
                entity_id="acme",
                capabilities=["permission_check", "authority_resolution", "human_escalation"],
                data_scopes=["roles", "policies", "delegations"],
            ),
        ]
        for user in self.workspace.users.values():
            delegates.append(
                Delegate(
                    id=f"delegate:user:{user.id}",
                    name=f"{user.name} Delegate",
                    kind="personal",
                    entity_id=user.id,
                    owner_user_id=user.id,
                    capabilities=["authorized_status", "expertise_context", "availability", "decision_boundary"],
                    data_scopes=[f"user:{user.id}", *[f"team:{team_id}" for team_id in user.team_ids]],
                    status="unavailable" if user.availability.status == "out_of_office" else "ready",
                )
            )
        for project in self.workspace.projects.values():
            delegates.append(
                Delegate(
                    id=f"delegate:project:{project.id}",
                    name=f"{project.name} Delegate",
                    kind="project",
                    entity_id=project.id,
                    capabilities=["project_status", "blocker_map", "decision_memory"],
                    data_scopes=[f"project:{project.id}"],
                )
            )
        for team in self.workspace.teams.values():
            delegates.append(
                Delegate(
                    id=f"delegate:team:{team.id}",
                    name=f"{team.name} Delegate",
                    kind="team",
                    entity_id=team.id,
                    capabilities=["team_status", "expertise_routing", "policy_context"],
                    data_scopes=[f"team:{team.id}"],
                )
            )
        for policy in self.workspace.policies.values():
            delegates.append(
                Delegate(
                    id=f"delegate:policy:{policy.id}",
                    name=f"{policy.key} Policy Delegate",
                    kind="policy",
                    entity_id=policy.id,
                    capabilities=["policy_lookup", "control_evaluation"],
                    data_scopes=[policy.scope],
                )
            )
        return delegates

    def response(self) -> RegistryResponse:
        relationships: list[dict[str, str]] = []
        for user in self.workspace.users.values():
            for team_id in user.team_ids:
                relationships.append({"from": user.id, "type": "member_of", "to": team_id})
            for project_id in user.project_ids:
                relationships.append({"from": user.id, "type": "works_on", "to": project_id})
        for project in self.workspace.projects.values():
            for blocker_id in project.blocker_ids:
                relationships.append({"from": blocker_id, "type": "blocks", "to": project.id})
        for delegation in self.workspace.delegations.values():
            relationships.append({"from": delegation.from_user_id, "type": "delegates_to", "to": delegation.to_user_id})
        return RegistryResponse(delegates=self.delegates(), relationships=relationships)
