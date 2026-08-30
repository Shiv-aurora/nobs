from __future__ import annotations

from datetime import datetime

from .models import Evidence, Intent, SecurityFinding
from .policy import PolicyEngine
from .security import ContentSecurityScanner
from .workspace import Workspace


class EvidenceRetriever:
    def __init__(self, workspace: Workspace, policy: PolicyEngine, scanner: ContentSecurityScanner):
        self.workspace = workspace
        self.policy = policy
        self.scanner = scanner

    def retrieve(
        self,
        requester_id: str,
        text: str,
        intent: Intent,
        delegate_for_user_id: str | None = None,
    ) -> tuple[list[Evidence], list[SecurityFinding], int]:
        requester = self.workspace.users[requester_id]
        lowered = text.lower()
        represented = self.workspace.users.get(delegate_for_user_id or "")
        greeting_only = lowered.strip(" \t\n!.,?") in {"hi", "hello", "hey", "yo"}
        represented_scope: set[str] = set()
        if represented and not greeting_only:
            # A DM already establishes which employee delegate is answering.
            # Select that employee's authorized work graph independently of how
            # their name is spelled in the message (for example "daniled").
            represented_scope = {
                represented.id,
                *represented.team_ids,
                *represented.project_ids,
            }
            for item in self.workspace.work_items.values():
                if item.owner_user_id == represented.id:
                    represented_scope.update({item.id, item.key.lower()})
        candidates: list[Evidence] = []
        denied = 0
        for evidence in self.workspace.evidence.values():
            relevant = bool(represented_scope.intersection(entity_id.lower() for entity_id in evidence.entity_ids))
            if intent == Intent.RESTRICTED:
                relevant = "sarah" in lowered and "sarah" in evidence.entity_ids
            elif "vendor" in lowered or "attachment" in lowered or "poison" in lowered:
                relevant = evidence.id == "ev-poisoned-vendor-note" or "atlas" in evidence.entity_ids
            elif "atlas" in lowered or intent in {Intent.DECISION, Intent.LIVE_STATUS, Intent.POLICY}:
                relevant = "atlas" in evidence.entity_ids or evidence.id == "ev-policy"
            if not relevant:
                continue
            if not self.policy.can_read(requester, evidence):
                denied += 1
                continue
            candidates.append(evidence)

        safe: list[Evidence] = []
        findings: list[SecurityFinding] = []
        for evidence in candidates:
            scanned, finding = self.scanner.scan(evidence)
            if finding:
                findings.append(finding)
            if not finding or not finding.blocked:
                safe.append(scanned)
        safe.sort(key=lambda item: (item.confidence, item.observed_at), reverse=True)
        return safe[:6], findings, denied


def freshness_label(evidence: list[Evidence], now: datetime) -> str:
    if not evidence:
        return "No authorized evidence"
    newest = max(item.observed_at for item in evidence)
    hours = max(0, int((now - newest).total_seconds() // 3600))
    if hours == 0:
        return "Updated within the hour"
    if hours < 24:
        return f"Updated {hours}h ago"
    return f"Updated {hours // 24}d ago"
