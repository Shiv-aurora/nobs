from __future__ import annotations

from app.models import QueryRequest, RunStatus


def test_factual_answer_routes_across_departments_without_interrupting(services):
    result = services.orchestrator.run(QueryRequest(requester_id="maya", text="Why has Atlas not shipped?"))

    assert result.status == RunStatus.ANSWERED
    assert result.people_interrupted == 0
    assert "SEC-184" in result.answer
    assert [step.delegate_id for step in result.route] == [
        "delegate:user:maya",
        "delegate:project:atlas",
        "delegate:team:engineering",
        "delegate:team:security",
    ]
    assert len(result.evidence) >= 4
    assert all(item.scope != "hr" for item in result.evidence)


def test_live_work_state_and_delegated_approver(services):
    result = services.orchestrator.run(
        QueryRequest(requester_id="maya", text="Who is handling the Atlas blocker, and can I get an answer tonight?")
    )

    assert result.status == RunStatus.ANSWERED
    assert "Daniel Kim" in result.answer
    assert "Alex Morgan" in result.answer
    assert "out through" in result.answer
    assert result.people_interrupted == 0


def test_high_impact_request_escalates_to_valid_human_authority(services):
    result = services.orchestrator.run(
        QueryRequest(
            requester_id="maya",
            text="A customer will pay $200K if Atlas launches tomorrow. Can we bypass the security review?",
        )
    )

    assert result.status == RunStatus.ESCALATED
    assert result.people_interrupted == 1
    assert result.decision_id
    decision = services.workspace.decisions[result.decision_id]
    assert decision.assignee_id == "alex"
    assert result.decision_assignee_id == "alex"
    assert decision.canonical_key == "atlas_security_exception"
    assert len(services.workspace.decisions) == 1


def test_identical_pending_request_does_not_create_duplicate_interrupt(services):
    request = QueryRequest(requester_id="maya", text="Can we bypass Atlas security review for the $200K customer?")
    first = services.orchestrator.run(request)
    second = services.orchestrator.run(request)

    assert first.decision_id == second.decision_id
    assert len(services.workspace.decisions) == 1
    assert services.workspace.stats["human_interruptions"] == 1


def test_restricted_employee_data_refused_before_exposure(services):
    result = services.orchestrator.run(QueryRequest(requester_id="maya", text="What is Sarah's salary?"))

    assert result.status == RunStatus.REFUSED
    assert result.people_interrupted == 0
    assert result.evidence == []
    assert "restricted" in result.answer.lower()
    assert services.workspace.stats["restricted_requests_blocked"] == 1


def test_poisoned_content_is_quarantined_and_excluded(services):
    result = services.orchestrator.run(
        QueryRequest(requester_id="maya", text="Does the vendor attachment change the Atlas launch status?")
    )

    assert result.status == RunStatus.ANSWERED
    assert len(result.security_findings) == 1
    assert result.security_findings[0].blocked is True
    assert "ev-poisoned-vendor-note" not in [item.id for item in result.evidence]
    assert "blocked" in result.answer.lower()


def test_ai_cost_guard_blocks_new_synthesis_but_not_policy(services):
    services.orchestrator.ai_enabled = False
    result = services.orchestrator.run(QueryRequest(requester_id="maya", text="Why has Atlas not shipped?"))

    assert result.status == RunStatus.FAILED
    assert result.policy_result == "ai_enabled=false"
    assert result.people_interrupted == 0
