from __future__ import annotations


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


def test_checkpoint_rejects_actor_without_meeting_authority(client) -> None:
    run = prepare_launch(client)
    mission = client.get(f"/v1/missions/{run['mission_id']}", params={"user_id": "shivam"}).json()

    denied = client.post(
        f"/v1/checkpoints/{mission['checkpoint_id']}/resolve",
        json={"actor_id": "maya", "decision": "approved", "rationale": "I approve this action."},
    )

    assert denied.status_code == 403
    unchanged = client.get(f"/v1/missions/{run['mission_id']}", params={"user_id": "shivam"}).json()
    assert unchanged["status"] == "waiting_human"


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
    assert len(mission["proposed_commands"]) == 1
    assert mission["proposed_commands"][0]["expected_etag"] == "google-etag-v7"

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
