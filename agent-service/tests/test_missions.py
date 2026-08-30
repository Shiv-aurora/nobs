from __future__ import annotations

from app.missions import _PlanOutput, _SpecialistOutput


def test_controller_model_cannot_choose_executable_agent_ids_or_route_coverage() -> None:
    assert set(_PlanOutput.model_fields) == {"objective", "authority_required"}


def test_specialist_schema_bounds_structured_output_to_fit_the_model_budget() -> None:
    schema = _SpecialistOutput.model_json_schema()

    assert schema["properties"]["findings"]["maxItems"] == 4
    assert schema["properties"]["claims"]["maxItems"] == 4
    assert schema["properties"]["unresolved_questions"]["maxItems"] == 2


def prepare_launch(client):
    response = client.post(
        "/v1/meetings/meeting-atlas-launch-readiness/prepare",
        json={"actor_id": "shivam", "trigger": "manual"},
    )
    assert response.status_code == 200
    return response.json()


def test_parallel_specialists_execute_as_distinct_versioned_nodes(client) -> None:
    run = prepare_launch(client)
    mission = client.get(f"/v1/missions/{run['mission_id']}", params={"user_id": "shivam"}).json()
    reports = mission["specialist_reports"]

    assert [item["agent_id"] for item in reports] == [
        "agent:work-graph-specialist",
        "agent:policy-evidence-specialist",
    ]
    assert all(item["agent_version"] == "1.0.0" for item in reports)
    assert reports[0]["started_at"] == reports[1]["started_at"]
    assert all(item["duration_ms"] >= 0 for item in reports)


def test_prompt_injection_and_restricted_evidence_never_enter_mission_claims(client) -> None:
    run = prepare_launch(client)
    mission = client.get(f"/v1/missions/{run['mission_id']}", params={"user_id": "shivam"}).json()
    source_refs = {
        claim["source_ref"]
        for report in mission["specialist_reports"]
        for claim in report["claims"]
    }

    assert "evidence:ev-poisoned-vendor-note" not in source_refs
    assert all("salary" not in claim["statement"].lower() for report in mission["specialist_reports"] for claim in report["claims"])


def test_resume_is_idempotent_after_every_node_is_persisted(client) -> None:
    run = prepare_launch(client)
    mission_id = run["mission_id"]
    before = client.get(f"/v1/missions/{mission_id}/steps", params={"user_id": "shivam"}).json()

    resumed = client.post(
        f"/v1/missions/{mission_id}/resume",
        json={"actor_id": "shivam", "trigger": "manual"},
    )
    after = client.get(f"/v1/missions/{mission_id}/steps", params={"user_id": "shivam"}).json()

    assert resumed.status_code == 200
    assert resumed.json()["status"] == "waiting_human"
    assert [(item["id"], item["attempt"]) for item in after] == [
        (item["id"], item["attempt"]) for item in before
    ]


def test_business_and_calendar_authority_are_separate_persisted_gates(client, services) -> None:
    meeting = services.workspace.meetings["meeting-atlas-launch-readiness"].model_copy(deep=True)
    meeting.id = "meeting-google-test-launch"
    meeting.calendar_event_id = "google-event-test-launch"
    meeting.source = "google_calendar"
    meeting.etag = "google-launch-etag-v1"
    meeting.preparation_status = "not_started"
    meeting.prep_run_id = None
    services.workspace.save_meeting(meeting)

    prepared = client.post(
        f"/v1/meetings/{meeting.id}/prepare",
        json={"actor_id": "shivam", "trigger": "manual"},
    )
    assert prepared.status_code == 200
    mission_id = prepared.json()["mission_id"]
    mission = client.get(f"/v1/missions/{mission_id}", params={"user_id": "shivam"}).json()
    business_checkpoint_id = mission["business_checkpoint_id"]

    assert mission["current_stage"] == "waiting_business_decision"
    assert mission["calendar_checkpoint_id"] is None
    assert next(item for item in mission["resolutions"] if item["agenda_item_id"] == "launch-security")["authority_type"] == "atlas_security_approval"
    assert services.workspace.human_checkpoints[business_checkpoint_id].authorized_actor_ids == ["alex"]
    alex_detail = client.get(f"/v1/meetings/{meeting.id}", params={"user_id": "alex"})
    assert alex_detail.status_code == 200

    for actor_id in ("maya", "shivam"):
        denied = client.post(
            f"/v1/checkpoints/{business_checkpoint_id}/resolve",
            json={"actor_id": actor_id, "decision": "approved", "rationale": "I approve this business decision."},
        )
        assert denied.status_code == 403

    approved_business = client.post(
        f"/v1/checkpoints/{business_checkpoint_id}/resolve",
        json={"actor_id": "alex", "decision": "approved", "rationale": "Valid acting Security Approver accepts the bounded exception."},
    )
    assert approved_business.status_code == 200
    resumed = approved_business.json()
    calendar_checkpoint_id = resumed["calendar_checkpoint_id"]
    assert resumed["id"] == mission_id
    assert resumed["status"] == "waiting_human"
    assert resumed["current_stage"] == "waiting_calendar_action"
    assert calendar_checkpoint_id != business_checkpoint_id
    assert services.workspace.human_checkpoints[business_checkpoint_id].status == "approved"
    assert services.workspace.human_checkpoints[business_checkpoint_id].resolved_by == "alex"
    assert services.workspace.human_checkpoints[calendar_checkpoint_id].authorized_actor_ids == ["shivam"]
    assert services.mission_runtime.inspect(mission_id, meeting)["resumed_steps"] == ["calendar-action-gate"]

    for actor_id in ("maya", "alex"):
        denied_calendar = client.post(
            f"/v1/meetings/{meeting.id}/actions",
            json={"actor_id": actor_id, "action": "shorten", "expected_etag": meeting.etag, "duration_minutes": 15},
        )
        assert denied_calendar.status_code == 403
    denied_checkpoint = client.post(
        f"/v1/checkpoints/{calendar_checkpoint_id}/resolve",
        json={"actor_id": "alex", "decision": "approved", "rationale": "I approved the business decision, not the Calendar mutation."},
    )
    assert denied_checkpoint.status_code == 403

    approved_calendar = client.post(
        f"/v1/meetings/{meeting.id}/actions",
        json={"actor_id": "shivam", "action": "shorten", "expected_etag": meeting.etag, "duration_minutes": 15},
    )
    assert approved_calendar.status_code == 200
    queued = client.get(f"/v1/missions/{mission_id}", params={"user_id": "shivam"}).json()
    assert queued["status"] == "queued_action"
    assert services.workspace.human_checkpoints[calendar_checkpoint_id].status == "approved"
    assert services.workspace.human_checkpoints[calendar_checkpoint_id].resolved_by == "shivam"
    command = queued["proposed_commands"][0]
    assert command["checkpoint_id"] == calendar_checkpoint_id
    assert command["business_checkpoint_id"] == business_checkpoint_id
    assert command["approval_decision_id"] == business_checkpoint_id
    assert [event.event_type for event in services.workspace.audit if mission_id in event.entity_ids and event.event_type.startswith("mission.")][-2:] == [
        "mission.business_decision_resolved",
        "mission.calendar_action_resolved",
    ]


def test_checkpoint_rejects_actor_without_business_authority(client) -> None:
    run = prepare_launch(client)
    mission = client.get(f"/v1/missions/{run['mission_id']}", params={"user_id": "shivam"}).json()

    denied = client.post(
        f"/v1/checkpoints/{mission['checkpoint_id']}/resolve",
        json={"actor_id": "maya", "decision": "approved", "rationale": "I approve this action."},
    )

    assert denied.status_code == 403
    unchanged = client.get(f"/v1/missions/{run['mission_id']}", params={"user_id": "shivam"}).json()
    assert unchanged["status"] == "waiting_human"


def test_meeting_detail_exposes_compact_mission_inspector(client) -> None:
    run = prepare_launch(client)
    detail = client.get(
        "/v1/meetings/meeting-atlas-launch-readiness",
        params={"user_id": "shivam"},
    ).json()
    inspector = detail["mission_inspector"]

    assert inspector["mission_id"] == run["mission_id"]
    assert inspector["workflow_version"] == "1.1.0"
    assert inspector["policy_version"] == "1.1.0"
    assert inspector["trace_id"]
    assert inspector["business_checkpoint"]["authorized_people"] == [{"id": "alex", "name": "Alex Morgan"}]
    assert inspector["calendar_checkpoint"]["status"] == "not_started"
    assert inspector["calendar_checkpoint"]["authorized_people"] == [{"id": "shivam", "name": "Shivam Arora"}]
    assert inspector["accepted_evidence_count"] > 0
    assert inspector["quarantined_evidence_count"] > 0
    assert inspector["command"] is None
    assert inspector["steps"][-1]["label"] == "Action Executor"


def test_preference_memory_is_explicitly_non_authoritative(client) -> None:
    response = client.post(
        "/v1/preferences",
        json={"actor_id": "maya", "key": "brief_detail", "value": "concise"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "stored", "backend": "local_test", "authority_effect": "none"}


def test_work_event_rejects_credential_shaped_payload(client) -> None:
    response = client.post("/v1/events", json={
        "id": "bad-event",
        "source": "github",
        "event_type": "pull_request.opened",
        "actor_user_id": "daniel",
        "entity_ids": ["atlas"],
        "occurred_at": "2026-08-30T12:00:00Z",
        "payload": {"access_token": "must-not-enter-the-event-bus"},
    })
    assert response.status_code == 422


def test_real_calendar_source_proposes_and_queues_only_an_approved_command(client, services) -> None:
    meeting = services.workspace.meetings["meeting-atlas-engineering-sync"].model_copy(deep=True)
    meeting.id = "meeting-google-test-engineering"
    meeting.calendar_event_id = "google-event-test-engineering"
    meeting.source = "google_calendar"
    meeting.etag = "google-etag-v7"
    meeting.preparation_status = "not_started"
    meeting.prep_run_id = None
    meeting.pending_action = "none"
    meeting.approved_recommendation = "none"
    services.workspace.save_meeting(meeting)

    prepared = client.post(
        f"/v1/meetings/{meeting.id}/prepare",
        json={"actor_id": "shivam", "trigger": "manual"},
    )
    mission = client.get(
        f"/v1/missions/{prepared.json()['mission_id']}",
        params={"user_id": "shivam"},
    ).json()
    assert mission["status"] == "waiting_human"
    assert mission["proposed_commands"] == []

    approved = client.post(
        f"/v1/meetings/{meeting.id}/actions",
        json={"actor_id": "shivam", "action": "cancel", "expected_etag": "google-etag-v7"},
    )
    assert approved.status_code == 200
    assert approved.json()["pending_action"] == "cancel"
    queued = client.get(
        f"/v1/missions/{prepared.json()['mission_id']}",
        params={"user_id": "shivam"},
    ).json()
    assert queued["status"] == "queued_action"
    assert queued["proposed_commands"][0]["status"] == "queued"
    assert queued["proposed_commands"][0]["expected_etag"] == "google-etag-v7"
    assert queued["proposed_commands"][0]["approval_decision_id"] == queued["checkpoint_id"]


def test_access_gate_is_the_first_persisted_deterministic_step(client) -> None:
    run = prepare_launch(client)
    steps = client.get(
        f"/v1/missions/{run['mission_id']}/steps",
        params={"user_id": "shivam"},
    ).json()

    assert steps[0]["node_id"] == "access-gate"
    assert steps[0]["node_kind"] == "access_gate"
    assert steps[0]["status"] == "completed"
    assert steps[0]["output_refs"] == ["authorized:meeting-member"]
