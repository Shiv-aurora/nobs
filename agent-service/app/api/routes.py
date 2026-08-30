from __future__ import annotations

from datetime import datetime, timedelta
import json
from queue import Queue
from threading import Thread

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, WebSocket, status
from fastapi.responses import StreamingResponse

from ..models import (
    AuditEvent,
    BootstrapResponse,
    DelegationResolution,
    DelegationResolutionRequest,
    DecisionResolution,
    DecisionStatus,
    HealthResponse,
    MeetingActionRequest,
    MeetingAttendanceRequest,
    MeetingDelegationAction,
    MeetingDelegationCreate,
    MeetingDelegationUpdate,
    MeetingPreparationRequest,
    OOOQueueItem,
    OOOQueueCreate,
    OOOUpdateRequest,
    QueryRequest,
    QueryResult,
    RegistryResponse,
    WorkEvent,
)
from ..mission_models import MissionCheckpointResolution
from ..pubsub import PubSubPushEnvelope
from ..preferences import PreferenceWrite
from ..rate_limit import RateLimitExceeded
from ..service import Services
from ..live_adapter import MeetingLiveAdapter


router = APIRouter()


def get_services(request: Request) -> Services:
    return request.app.state.services


@router.get("/healthz", response_model=HealthResponse)
@router.get("/v1/health", response_model=HealthResponse)
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
        organization_id=str(services.workspace.organization["id"]),
        current_user=services.workspace.users[user_id],
        projects=list(services.workspace.projects.values()),
        needs_you=decisions,
        work_states=services.work_state.project(),
        attention_metrics=attention_metrics,
    )


@router.post("/v1/delegation/resolve", response_model=DelegationResolution)
def resolve_delegation(
    payload: DelegationResolutionRequest,
    services: Services = Depends(get_services),
) -> DelegationResolution:
    # This preflight is deliberately outside query admission: it performs no
    # retrieval or model work and therefore does not burn a user's AI allowance.
    return services.router.resolve_delegation(payload)


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


@router.post("/v1/query/stream")
def query_stream(payload: QueryRequest, services: Services = Depends(get_services)) -> StreamingResponse:
    events: Queue[dict | None] = Queue()

    def emit(phase: str, data: dict) -> None:
        events.put({"event": phase, "data": data})

    def work() -> None:
        acquired = False
        try:
            services.rate_limiter.acquire(payload.requester_id)
            acquired = True
            emit("accepted", {"requester_id": payload.requester_id})
            result = services.orchestrator.run(payload, progress=emit)
            emit("completed", {"result": result.model_dump(mode="json")})
        except RateLimitExceeded as exc:
            emit("failed", {"detail": str(exc), "retry_after": exc.retry_after, "status": 429})
        except Exception:
            # Do not stream internal exception text across the service boundary.
            emit("failed", {"detail": "The organizational agent could not complete this request.", "status": 500})
        finally:
            if acquired:
                services.rate_limiter.release()
            events.put(None)

    Thread(target=work, daemon=True).start()

    def stream():
        while True:
            item = events.get()
            if item is None:
                return
            yield json.dumps(item, separators=(",", ":")) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@router.get("/v1/runs/{run_id}", response_model=QueryResult)
def get_run(run_id: str, services: Services = Depends(get_services)) -> QueryResult:
    result = services.workspace.query_results.get(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@router.get("/v1/meetings")
def meetings(user_id: str = Query(...), services: Services = Depends(get_services)):
    if user_id not in services.workspace.users and user_id != "shivam":
        raise HTTPException(status_code=404, detail="User not found")
    return services.meetings.list_for_user(user_id)


@router.get("/v1/meetings/{meeting_id}")
def meeting(meeting_id: str, user_id: str = Query(...), services: Services = Depends(get_services)):
    result = services.meetings.get_for_user(meeting_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Meeting not found")
    run = services.workspace.meeting_runs.get(result.prep_run_id or "")
    current_mission = services.workspace.missions.get(run.mission_id or "") if run else None
    if run and (
        not current_mission
        or current_mission.workflow_version != services.mission_runtime.WORKFLOW_VERSION
    ):
        # Legacy pre-mission projections remain in storage for audit history,
        # but are never presented as current executable-agent results. A new
        # workflow version must be prepared into a new mission explicitly.
        run = None
    delegation = services.meeting_delegations.for_meeting(meeting_id, user_id)
    handoff = services.meeting_delegations.handoff(delegation) if delegation else None
    inspector = (
        services.mission_runtime.inspect(run.mission_id, result)
        if run and run.mission_id and run.mission_id in services.workspace.missions
        else None
    )
    return {"meeting": result, "run": run, "delegation": delegation, "handoff": handoff, "mission_inspector": inspector}


@router.post("/v1/meetings/{meeting_id}/delegations")
def create_meeting_delegation(meeting_id: str, payload: MeetingDelegationCreate, services: Services = Depends(get_services)):
    meeting = services.meetings.get_for_user(meeting_id, payload.actor_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    try:
        return services.meeting_delegations.create(meeting, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/v1/meetings/{meeting_id}/attendance")
def update_meeting_attendance(meeting_id: str, payload: MeetingAttendanceRequest, services: Services = Depends(get_services)):
    meeting = services.meetings.get_for_user(meeting_id, payload.actor_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    try:
        return services.meeting_delegations.set_attendance(meeting, payload.actor_id, payload.choice)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/v1/meeting-delegations/{delegation_id}")
def meeting_delegation(delegation_id: str, user_id: str = Query(...), services: Services = Depends(get_services)):
    try:
        delegation = services.meeting_delegations.get(delegation_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {
        "delegation": delegation,
        "session": services.meeting_delegations.session_for(delegation.id),
        "handoff": services.meeting_delegations.handoff(delegation),
        "meeting": services.workspace.meetings[delegation.meeting_id],
    }


@router.patch("/v1/meeting-delegations/{delegation_id}/mission")
def update_meeting_delegation(delegation_id: str, payload: MeetingDelegationUpdate, services: Services = Depends(get_services)):
    try:
        delegation = services.meeting_delegations.get(delegation_id, payload.actor_id)
        return services.meeting_delegations.update(delegation, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/v1/meeting-delegations/{delegation_id}/start")
def start_meeting_delegation(delegation_id: str, payload: MeetingDelegationAction, services: Services = Depends(get_services)):
    try:
        services.rate_limiter.acquire(payload.actor_id)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    try:
        delegation = services.meeting_delegations.get(delegation_id, payload.actor_id)
        delegation, session, nonce = services.meeting_delegations.start(delegation)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        services.rate_limiter.release()
    return {"delegation": delegation, "session": session, "session_nonce": nonce}


@router.post("/v1/meeting-delegations/{delegation_id}/end")
def end_meeting_delegation(delegation_id: str, payload: MeetingDelegationAction, services: Services = Depends(get_services)):
    try:
        delegation = services.meeting_delegations.get(delegation_id, payload.actor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    existing = services.meeting_delegations.handoff(delegation)
    return existing or services.meeting_delegations.end(delegation)


@router.post("/v1/meeting-delegations/{delegation_id}/revoke")
def revoke_meeting_delegation(delegation_id: str, payload: MeetingDelegationAction, services: Services = Depends(get_services)):
    try:
        delegation = services.meeting_delegations.get(delegation_id, payload.actor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    existing = services.meeting_delegations.handoff(delegation)
    return existing or services.meeting_delegations.end(delegation, revoked=True)


@router.get("/v1/meeting-delegations/{delegation_id}/handoff")
def meeting_delegation_handoff(delegation_id: str, user_id: str = Query(...), services: Services = Depends(get_services)):
    try:
        delegation = services.meeting_delegations.get(delegation_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    handoff = services.meeting_delegations.handoff(delegation)
    if not handoff:
        raise HTTPException(status_code=404, detail="The meeting handoff is not ready")
    return handoff


@router.websocket("/v1/live/meetings/{delegation_id}")
async def live_meeting(websocket: WebSocket, delegation_id: str, user_id: str = Query(...), nonce: str = Query(...)):
    services: Services = websocket.app.state.services
    services.meeting_delegations.expire_abandoned_sessions()
    try:
        delegation = services.meeting_delegations.get(delegation_id, user_id)
    except (KeyError, PermissionError):
        await websocket.close(code=4403, reason="Meeting delegation not found")
        return
    session = services.meeting_delegations.session_for(delegation.id)
    if not session or not services.meeting_delegations.verify_nonce(session, nonce):
        await websocket.close(code=4401, reason="Invalid live session")
        return
    if session.status not in {"connecting", "reconnecting"}:
        await websocket.close(code=4409, reason="The live session already has a connection or has ended")
        return
    if session.status == "reconnecting":
        if session.reconnect_attempts >= services.settings.live_max_reconnect_attempts:
            await websocket.close(code=4429, reason="Live reconnect limit reached")
            return
        session.reconnect_attempts += 1
        session.updated_at = services.meeting_delegations.now_fn()
        services.workspace.save_live_meeting_session(session)
    await MeetingLiveAdapter(services).serve(websocket, delegation, session)


@router.post("/v1/meetings/{meeting_id}/prepare")
def prepare_meeting(meeting_id: str, payload: MeetingPreparationRequest, services: Services = Depends(get_services)):
    result = services.meetings.get_for_user(meeting_id, payload.actor_id)
    if not result:
        raise HTTPException(status_code=404, detail="Meeting not found")
    try:
        return services.meetings.prepare(result, payload.actor_id, payload.trigger)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail="Meeting preparation could not complete safely. Please try again.",
        ) from exc


@router.post("/v1/meetings/{meeting_id}/actions")
def confirm_meeting_action(meeting_id: str, payload: MeetingActionRequest, services: Services = Depends(get_services)):
    result = services.meetings.get_for_user(meeting_id, payload.actor_id)
    if not result:
        raise HTTPException(status_code=404, detail="Meeting not found")
    try:
        return services.meetings.confirm_action(result, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/v1/ooo")
def update_ooo(payload: OOOUpdateRequest, services: Services = Depends(get_services)):
    person = services.workspace.users.get(payload.actor_id)
    if not person:
        raise HTTPException(status_code=404, detail="User not found")
    person.availability.status = "out_of_office" if payload.enabled else "available"
    person.availability.until = payload.until if payload.enabled else None
    person.availability.delegate_user_id = payload.delegate_user_id if payload.enabled else None
    services.workspace.append_audit(AuditEvent(
        event_type="availability.ooo_enabled" if payload.enabled else "availability.ooo_disabled",
        actor_id=payload.actor_id,
        entity_ids=[payload.actor_id],
        summary="OOO mode enabled; the delegate will queue routine work." if payload.enabled else "OOO mode ended; the return digest is ready.",
        created_at=services.now_fn(),
        metadata={"until": payload.until.isoformat() if payload.until else None, "delegate_user_id": payload.delegate_user_id},
    ))
    return {"availability": person.availability, "queued": len([item for item in services.workspace.ooo_queue.values() if item.user_id == payload.actor_id])}


@router.get("/v1/ooo/digest")
def ooo_digest(user_id: str = Query(...), services: Services = Depends(get_services)):
    items: list[OOOQueueItem] = [item for item in services.workspace.ooo_queue.values() if item.user_id == user_id]
    return {"user_id": user_id, "items": items, "total": len(items), "urgent": len([item for item in items if item.urgent])}


@router.post("/v1/ooo/queue")
def queue_ooo_activity(payload: OOOQueueCreate, services: Services = Depends(get_services)):
    person = services.workspace.users.get(payload.user_id)
    if not person:
        raise HTTPException(status_code=404, detail="User not found")
    if person.availability.status != "out_of_office":
        return {"queued": False}
    existing = next((item for item in services.workspace.ooo_queue.values() if item.user_id == payload.user_id and item.source_id == payload.source_id), None)
    if existing:
        return {"queued": True, "item": existing}
    item = OOOQueueItem(**payload.model_dump(), created_at=services.now_fn())
    services.workspace.save_ooo_queue_item(item)
    return {"queued": True, "item": item}


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


@router.get("/v1/executable-agents")
def executable_agents(services: Services = Depends(get_services)):
    return services.executable_registry.response()


@router.get("/v1/executable-agents/{service_id}")
def executable_agent(service_id: str, services: Services = Depends(get_services)):
    try:
        return services.executable_registry.get_by_service_id(service_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Executable agent not found") from exc


@router.post("/v1/preferences")
def save_preference(payload: PreferenceWrite, services: Services = Depends(get_services)):
    if payload.actor_id not in services.workspace.users:
        raise HTTPException(status_code=404, detail="User not found")
    return services.preference_memory.write(payload)


@router.get("/v1/missions/{mission_id}")
def get_mission(mission_id: str, user_id: str = Query(...), services: Services = Depends(get_services)):
    mission = services.workspace.missions.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if not services.meetings.get_for_user(mission.meeting_id, user_id):
        raise HTTPException(status_code=403, detail="Mission is outside the user's meeting scope")
    return mission


@router.get("/v1/missions/{mission_id}/steps")
def get_mission_steps(mission_id: str, user_id: str = Query(...), services: Services = Depends(get_services)):
    mission = services.workspace.missions.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if not services.meetings.get_for_user(mission.meeting_id, user_id):
        raise HTTPException(status_code=403, detail="Mission is outside the user's meeting scope")
    return sorted(
        [item for item in services.workspace.mission_steps.values() if item.mission_id == mission_id],
        key=lambda item: item.ordinal,
    )


@router.post("/v1/missions/{mission_id}/resume")
def resume_mission(mission_id: str, payload: MeetingPreparationRequest, services: Services = Depends(get_services)):
    mission = services.workspace.missions.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    meeting = services.meetings.get_for_user(mission.meeting_id, payload.actor_id)
    if not meeting:
        raise HTTPException(status_code=403, detail="Mission is outside the user's meeting scope")
    return services.mission_runtime.resume(mission_id, meeting)


@router.post("/v1/checkpoints/{checkpoint_id}/resolve")
def resolve_mission_checkpoint(
    checkpoint_id: str,
    payload: MissionCheckpointResolution,
    services: Services = Depends(get_services),
):
    checkpoint = services.workspace.human_checkpoints.get(checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    mission = services.workspace.missions[checkpoint.mission_id]
    meeting = services.workspace.meetings[mission.meeting_id]
    try:
        return services.mission_runtime.resolve_checkpoint(checkpoint_id, payload, meeting)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/v1/audit")
def audit(limit: int = Query(default=50, ge=1, le=200), services: Services = Depends(get_services)):
    return list(reversed(services.workspace.audit[-limit:]))


def _ingest_work_event(event: WorkEvent, services: Services) -> dict:
    created = services.work_state.ingest(event)
    if created:
        if event.event_type.startswith("calendar.meeting."):
            meeting = services.meetings.upsert_from_calendar_event(event)
            if meeting and meeting.preparation_eligibility == "eligible" and meeting.preparation_status in {"not_started", "stale"}:
                until_start = meeting.start_at - services.now_fn()
                if timedelta(0) <= until_start <= timedelta(minutes=35):
                    services.meetings.prepare(meeting, meeting.organizer_user_id, "scheduled")
        services.workspace.append_audit(AuditEvent(
            event_type="work_state.updated",
            actor_id=event.actor_user_id,
            entity_ids=event.entity_ids,
            summary=f"{event.source} event {event.event_type} updated semantic work state.",
            created_at=event.occurred_at,
            metadata={"event_id": event.id},
        ))
    return {"accepted": created, "states": services.work_state.project()}


@router.post("/v1/events")
def ingest_event(event: WorkEvent, services: Services = Depends(get_services)):
    return _ingest_work_event(event, services)


@router.post("/v1/events/pubsub")
def ingest_pubsub_event(envelope: PubSubPushEnvelope, services: Services = Depends(get_services)):
    try:
        event = envelope.decode_work_event()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = _ingest_work_event(event, services)
    result["message_id"] = envelope.message.message_id
    return result


@router.post("/v1/demo/reset")
def reset_demo(services: Services = Depends(get_services)):
    if not services.settings.demo_mode:
        raise HTTPException(status_code=403, detail="Demo reset is disabled")
    services.workspace.reset_demo()
    services.meetings.reset_demo()
    services.rate_limiter.reset()
    services.usage_guard.reset()
    return {"status": "reset"}


@router.get("/v1/metrics")
def metrics(services: Services = Depends(get_services)):
    stats = services.workspace.stats.copy()
    stats["active_runs"] = services.rate_limiter.active_runs
    stats["delegates"] = len(services.registry.delegates())
    stats["decision_memories"] = len(services.workspace.memories)
    return stats
