from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from .adapters.model import ModelAdapter
from .evidence import EvidenceRetriever, freshness_label
from .intent import canonical_key, classify_intent
from .memory import DecisionMemoryStore
from .models import (
    AuditEvent,
    Decision,
    DecisionOption,
    Intent,
    QueryRequest,
    QueryResult,
    RunStatus,
)
from .policy import PolicyEngine
from .routing import OrganizationRouter
from .workspace import Workspace


class Orchestrator:
    def __init__(
        self,
        *,
        workspace: Workspace,
        model: ModelAdapter,
        policy: PolicyEngine,
        retriever: EvidenceRetriever,
        router: OrganizationRouter,
        memory: DecisionMemoryStore,
        now_fn,
        ai_enabled: bool = True,
    ):
        self.workspace = workspace
        self.model = model
        self.policy = policy
        self.retriever = retriever
        self.router = router
        self.memory = memory
        self.now_fn = now_fn
        self.ai_enabled = ai_enabled

    def _facts_hash(self) -> str:
        facts = {
            "atlas": self.workspace.projects["atlas"].model_dump(mode="json"),
            "sec184": self.workspace.work_items["sec-184"].model_dump(mode="json"),
            "policy": self.workspace.policies["sec-pol-12"].model_dump(mode="json"),
            "delegations": [item.model_dump(mode="json") for item in self.workspace.delegations.values()],
        }
        encoded = json.dumps(facts, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()[:16]

    def run(self, request: QueryRequest) -> QueryResult:
        now: datetime = self.now_fn()
        if request.requester_id not in self.workspace.users:
            raise KeyError(f"unknown requester: {request.requester_id}")
        intent = classify_intent(request.text)
        key = canonical_key(request.text, intent)
        route = self.router.build_route(request.requester_id, request.text, intent)
        evidence, findings, denied = self.retriever.retrieve(request.requester_id, request.text, intent)
        facts_hash = self._facts_hash()
        self.workspace.stats["queries_total"] += 1

        if findings:
            self.workspace.stats["poisoned_sources_blocked"] += len(findings)
            self.workspace.audit.append(AuditEvent(
                event_type="security.content_blocked",
                actor_id=request.requester_id,
                entity_ids=[finding.evidence_id for finding in findings],
                summary="Untrusted content was quarantined before synthesis.",
                created_at=now,
                metadata={"findings": [finding.model_dump(mode="json") for finding in findings]},
            ))

        if intent == Intent.RESTRICTED:
            self.workspace.stats["restricted_requests_blocked"] += 1
            result = QueryResult(
                requester_id=request.requester_id,
                query=request.text,
                intent=intent,
                status=RunStatus.REFUSED,
                headline="Access denied",
                answer="Compensation data is restricted to People Operations. No private employee record was retrieved or exposed.",
                route=[route[0]],
                evidence=[],
                confidence=1.0,
                freshness_label="Permission enforced before retrieval",
                people_interrupted=0,
                policy_result="Denied: requester lacks the HR role.",
                security_findings=findings,
                created_at=now,
                completed_at=self.now_fn(),
            )
            self.workspace.query_results[result.run_id] = result
            self.workspace.audit.append(AuditEvent(
                event_type="query.refused",
                actor_id=request.requester_id,
                entity_ids=["sarah", "people"],
                summary="Restricted employee-data request blocked.",
                created_at=now,
                metadata={"denied_evidence_count": denied},
            ))
            return result

        if intent == Intent.DECISION:
            valid_memory = self.memory.find_valid(key, "atlas", facts_hash)
            if valid_memory:
                self.workspace.stats["resolved_without_human"] += 1
                self.workspace.stats["cache_hits"] += 1
                decider = self.workspace.users[valid_memory.decided_by]
                result = QueryResult(
                    requester_id=request.requester_id,
                    query=request.text,
                    intent=intent,
                    status=RunStatus.ANSWERED,
                    headline="Existing decision applied",
                    answer=(
                        f"No. {decider.name} previously {valid_memory.outcome} this Atlas security exception: "
                        f"{valid_memory.rationale} The facts and governing policy have not changed, so no person was interrupted again."
                    ),
                    route=route,
                    evidence=evidence,
                    confidence=0.99,
                    freshness_label=freshness_label(evidence, now),
                    people_interrupted=0,
                    policy_result="Scoped decision memory matched current facts.",
                    security_findings=findings,
                    created_at=now,
                    completed_at=self.now_fn(),
                    cached=True,
                )
                self.workspace.query_results[result.run_id] = result
                return result

            authority = self.policy.resolve_authority("atlas_security_approval", "atlas")
            if not authority.assignee_id:
                answer = "No active Security Approver is available. The launch remains blocked under SEC-POL-12."
                result = QueryResult(
                    requester_id=request.requester_id,
                    query=request.text,
                    intent=intent,
                    status=RunStatus.REFUSED,
                    headline="No authorized approver available",
                    answer=answer,
                    route=route,
                    evidence=evidence,
                    confidence=1.0,
                    freshness_label=freshness_label(evidence, now),
                    people_interrupted=0,
                    policy_result=authority.reason,
                    security_findings=findings,
                    created_at=now,
                    completed_at=self.now_fn(),
                )
                self.workspace.query_results[result.run_id] = result
                return result

            existing = next((item for item in self.workspace.decisions.values() if item.canonical_key == key and item.status.value == "pending"), None)
            if existing:
                decision = existing
            else:
                decision = Decision(
                    canonical_key=key,
                    title="Atlas security exception",
                    summary="Northstar offered $200K if Atlas launches tomorrow, but SEC-184 is still pending and SEC-POL-12 requires an active Security Approver.",
                    requester_id=request.requester_id,
                    assignee_id=authority.assignee_id,
                    project_id="atlas",
                    options=[
                        DecisionOption(id="approve", label="Approve exception", tone="positive"),
                        DecisionOption(id="reject", label="Reject exception", tone="negative"),
                        DecisionOption(id="discuss", label="Discuss", tone="neutral"),
                    ],
                    evidence_ids=[item.id for item in evidence],
                    policy_ids=["sec-pol-12"],
                    created_at=now,
                    due_at=now + timedelta(hours=2),
                    facts_hash=facts_hash,
                )
                self.workspace.decisions[decision.id] = decision
                self.workspace.stats["human_interruptions"] += 1
                self.workspace.audit.append(AuditEvent(
                    event_type="decision.created",
                    actor_id=request.requester_id,
                    entity_ids=[decision.id, decision.assignee_id, "atlas"],
                    summary="One complete decision card routed to the acting Security Approver.",
                    created_at=now,
                    metadata={"authority_reason": authority.reason},
                ))
            result = QueryResult(
                requester_id=request.requester_id,
                query=request.text,
                intent=intent,
                status=RunStatus.ESCALATED,
                headline="Human decision required",
                answer=f"SEC-POL-12 prevents an automatic waiver. {authority.reason} One complete decision card was sent to {self.workspace.users[decision.assignee_id].name}.",
                route=route,
                evidence=evidence,
                confidence=1.0,
                freshness_label=freshness_label(evidence, now),
                people_interrupted=1,
                decision_id=decision.id,
                policy_result="Human authority required; model is not permitted to decide.",
                security_findings=findings,
                created_at=now,
                completed_at=self.now_fn(),
            )
            self.workspace.query_results[result.run_id] = result
            return result

        if not self.ai_enabled:
            result = QueryResult(
                requester_id=request.requester_id,
                query=request.text,
                intent=intent,
                status=RunStatus.FAILED,
                headline="AI capacity paused",
                answer="New synthesis is temporarily disabled by the cost-control guard. Existing decisions and cached answers remain available.",
                route=route[:1],
                evidence=[],
                confidence=1.0,
                freshness_label="Cost control active",
                people_interrupted=0,
                policy_result="ai_enabled=false",
                security_findings=findings,
                created_at=now,
                completed_at=self.now_fn(),
            )
            self.workspace.query_results[result.run_id] = result
            return result

        answer = self.model.synthesize(text=request.text, intent=intent, evidence=evidence)
        self.workspace.stats["resolved_without_human"] += 1
        result = QueryResult(
            requester_id=request.requester_id,
            query=request.text,
            intent=intent,
            status=RunStatus.ANSWERED,
            headline="Answered by the organization",
            answer=answer,
            route=route,
            evidence=evidence,
            confidence=min((sum(item.confidence for item in evidence) / max(1, len(evidence))), 0.99),
            freshness_label=freshness_label(evidence, now),
            people_interrupted=0,
            policy_result="Authorized evidence only; no human authority required.",
            security_findings=findings,
            created_at=now,
            completed_at=self.now_fn(),
        )
        self.workspace.query_results[result.run_id] = result
        self.workspace.audit.append(AuditEvent(
            event_type="query.answered",
            actor_id=request.requester_id,
            entity_ids=["atlas"],
            summary="Cross-department answer returned without interrupting a person.",
            created_at=now,
            metadata={"route": [step.delegate_id for step in route], "evidence_ids": [item.id for item in evidence]},
        ))
        return result
