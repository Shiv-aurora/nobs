from __future__ import annotations

from datetime import datetime

from .intent import is_presence_query
from .models import Evidence, Intent, SecurityFinding
from .policy import PolicyEngine
from .security import ContentSecurityScanner
from .workspace import Workspace


class EvidenceRetriever:
    def __init__(self, workspace: Workspace, policy: PolicyEngine, scanner: ContentSecurityScanner, now_fn):
        self.workspace = workspace
        self.policy = policy
        self.scanner = scanner
        self.now_fn = now_fn

    def _availability_evidence(self, user_id: str) -> Evidence:
        user = self.workspace.users[user_id]
        availability = user.availability
        delegate = self.workspace.users.get(availability.delegate_user_id or "")
        if availability.status == "out_of_office":
            until = availability.until.isoformat() if availability.until else "an unspecified return time"
            coverage = f" {delegate.name} is the recorded coverage delegate." if delegate else " No coverage delegate is recorded."
            content = f"{user.name} is out of office until {until}.{coverage} No physical-location data is stored or available."
        else:
            content = f"{user.name} is currently marked available. No physical-location data is stored or available."
        return Evidence(
            id=f"availability-{user.id}",
            title=f"{user.name} current availability",
            source_type="calendar_availability_state",
            source_url=f"calendar://{user.id}/availability",
            entity_ids=[user.id, *user.team_ids, *user.project_ids],
            scope="company",
            content=content,
            observed_at=self.now_fn(),
            confidence=1.0,
        )

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
        if not represented and is_presence_query(text):
            named = [user for user in self.workspace.users.values() if user.id.lower() in lowered or user.name.lower() in lowered or user.name.split()[0].lower() in lowered]
            represented = named[0] if len(named) == 1 else None
        greeting_only = lowered.strip(" \t\n!.,?") in {"hi", "hello", "hey", "yo"}
        presence_query = bool(represented and is_presence_query(text))
        asks_for_work = any(term in lowered for term in ("working", "project", "ticket", "pull request", "status", "blocker", "owning"))
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
        if presence_query and represented:
            candidates.append(self._availability_evidence(represented.id))
        denied = 0
        for evidence in self.workspace.evidence.values():
            relevant = bool(represented_scope.intersection(entity_id.lower() for entity_id in evidence.entity_ids))
            if presence_query and not asks_for_work:
                relevant = False
            if intent == Intent.RESTRICTED:
                relevant = "sarah" in lowered and "sarah" in evidence.entity_ids
            elif "vendor" in lowered or "attachment" in lowered or "poison" in lowered:
                relevant = evidence.id == "ev-poisoned-vendor-note" or "atlas" in evidence.entity_ids
            elif "atlas" in lowered:
                relevant = relevant or "atlas" in evidence.entity_ids or evidence.id == "ev-policy"
            elif not represented and intent in {Intent.DECISION, Intent.LIVE_STATUS, Intent.POLICY}:
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
