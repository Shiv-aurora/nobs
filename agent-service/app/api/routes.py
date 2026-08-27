from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from ..models import (
    AuditEvent,
    BootstrapResponse,
    DecisionResolution,
    DecisionStatus,
    HealthResponse,
    QueryRequest,
    QueryResult,
    RegistryResponse,
    WorkEvent,
)
from ..rate_limit import RateLimitExceeded
from ..service import Services


router = APIRouter()


def get_services(request: Request) -> Services:
    return request.app.state.services


@router.get("/healthz", response_model=HealthResponse)
def health(services: Services = Depends(get_services)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        mode="demo" if services.settings.demo_mode else "google-cloud",
        ai_enabled=services.orchestrator.ai_enabled,
        version=services.settings.version,
    )


@router.get("/v1/bootstrap", response_model=BootstrapResponse)
def bootstrap(
    user_id: str = Query(default="maya"),
    services: Services = Depends(get_services),
) -> BootstrapResponse:
    if user_id not in services.workspace.users:
        raise HTTPException(status_code=404, detail="User not found")
    decisions = [item for item in services.workspace.decisions.values() if item.assignee_id == user_id and item.status == DecisionStatus.PENDING]
    stats = services.workspace.stats
    total = max(1, stats["queries_total"])
    attention_metrics = {
        **stats,
        "interruption_avoidance_rate": round(100 * stats["resolved_without_human"] / total, 1),
    }
    return BootstrapResponse(
        current_user=services.workspace.users[user_id],
        projects=list(services.workspace.projects.values()),
        needs_you=decisions,
        work_states=services.work_state.project(),
        attention_metrics=attention_metrics,
    )


@router.post("/v1/query", response_model=QueryResult)
def query(payload: QueryRequest, response: Response, services: Services = Depends(get_services)) -> QueryResult:
    try:
        services.rate_limiter.acquire(payload.requester_id)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    try:
        return services.orchestrator.run(payload)
    finally:
        services.rate_limiter.release()


@router.get("/v1/runs/{run_id}", response_model=QueryResult)
def get_run(run_id: str, services: Services = Depends(get_services)) -> QueryResult:
    result = services.workspace.query_results.get(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@router.get("/v1/decisions")
def decisions(
    assignee_id: str | None = None,
    services: Services = Depends(get_services),
):
    values = list(services.workspace.decisions.values())
    if assignee_id:
        values = [item for item in values if item.assignee_id == assignee_id]
    return values


@router.post("/v1/decisions/{decision_id}/resolve")
def resolve_decision(
    decision_id: str,
    payload: DecisionResolution,
    services: Services = Depends(get_services),
):
    decision = services.workspace.decisions.get(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.status != DecisionStatus.PENDING:
        raise HTTPException(status_code=409, detail="Decision already resolved")
    if not services.policy.actor_can_resolve(payload.actor_id, "atlas_security_approval"):
        raise HTTPException(status_code=403, detail="Actor does not hold the required authority")
    now: datetime = services.now_fn()
    decision.status = DecisionStatus(payload.status)
    decision.resolved_at = now
    decision.resolved_by = payload.actor_id
    decision.rationale = payload.rationale
    services.workspace.save_decision(decision)
    memory = services.memory.remember(decision)
    services.workspace.append_audit(AuditEvent(
        event_type="decision.resolved",
        actor_id=payload.actor_id,
        entity_ids=[decision.id, memory.id, "atlas"],
        summary=f"Atlas security exception {decision.status.value}; scoped decision memory created.",
        created_at=now,
        metadata={"rationale": payload.rationale, "memory_expires_at": memory.expires_at.isoformat()},
    ))
    return {"decision": decision, "memory": memory}


@router.get("/v1/registry", response_model=RegistryResponse)
def registry(services: Services = Depends(get_services)) -> RegistryResponse:
    return services.registry.response()


@router.get("/v1/audit")
def audit(limit: int = Query(default=50, ge=1, le=200), services: Services = Depends(get_services)):
    return list(reversed(services.workspace.audit[-limit:]))


@router.post("/v1/events")
def ingest_event(event: WorkEvent, services: Services = Depends(get_services)):
    created = services.work_state.ingest(event)
    return {"accepted": created, "states": services.work_state.project()}


@router.post("/v1/demo/reset")
def reset_demo(services: Services = Depends(get_services)):
    if not services.settings.demo_mode:
        raise HTTPException(status_code=403, detail="Demo reset is disabled")
    services.workspace.reset_demo()
    services.rate_limiter.reset()
    return {"status": "reset"}


@router.get("/v1/metrics")
def metrics(services: Services = Depends(get_services)):
    stats = services.workspace.stats.copy()
    stats["active_runs"] = services.rate_limiter.active_runs
    stats["delegates"] = len(services.registry.delegates())
    stats["decision_memories"] = len(services.workspace.memories)
    return stats
