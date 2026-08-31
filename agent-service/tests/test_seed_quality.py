from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STORYLINES = json.loads((ROOT / "seed" / "judge_storylines.json").read_text())


def test_every_judge_facing_conversation_has_a_substantial_storyline():
    assert STORYLINES["version"] == "2026-08-30-judge-polish-v2"
    assert set(STORYLINES["channel_updates"]) == {
        "town-square",
        "off-topic",
        "project-atlas",
        "project-relay",
        "security-review",
        "engineering",
        "customer-escalations",
        "launch-decisions",
    }
    assert all(len(updates) >= 4 for updates in STORYLINES["channel_updates"].values())

    assert set(STORYLINES["workroom_updates"]) == {
        "agent-workroom-atlas",
        "agent-workroom-pricing-launch-faq",
        "agent-workroom-support-taxonomy",
        "agent-workroom-northstar-onboarding",
        "agent-workroom-mobile-release-notes",
    }
    assert all(len(updates) >= 14 for updates in STORYLINES["workroom_updates"].values())
    assert all(len({update["author"] for update in updates}) >= 4 for updates in STORYLINES["workroom_updates"].values())
    assert all(sum(len(update["message"]) for update in updates) >= 2_000 for updates in STORYLINES["workroom_updates"].values())

    assert set(STORYLINES["dm_exchanges"]) == {"shivam", "sarah", "alex", "daniel", "priya", "helen"}
    for exchange in STORYLINES["dm_exchanges"].values():
        assert len(exchange) >= 5
        assert sum("delegate_scenario" in update for update in exchange) >= 2


def test_storyline_markers_and_delegate_scenarios_are_unique_and_readable():
    markers: list[str] = []
    scenarios: list[str] = []
    messages: list[str] = []
    for section in ("channel_updates", "workroom_updates"):
        for updates in STORYLINES[section].values():
            for update in updates:
                markers.append(update["marker"])
                messages.append(update["message"])
    for exchange in STORYLINES["dm_exchanges"].values():
        for update in exchange:
            messages.append(update["message"])
            if scenario := update.get("delegate_scenario"):
                scenarios.append(scenario)
            else:
                markers.append(update["marker"])

    assert len(markers) == len(set(markers))
    assert len(scenarios) == len(set(scenarios))
    assert all(len(message) >= 60 for message in messages)
    assert any("in review" in message.lower() for message in messages)
    assert any("quarantined" in message.lower() for message in messages)
    assert any("humans interrupted" in message.lower() for message in messages)


def test_calendar_has_many_meetings_and_three_seeded_mission_proofs(services):
    meetings = services.meetings.list_for_user("maya")
    meeting_ids = {meeting.id for meeting in meetings}
    assert len(meetings) >= 10
    assert set(STORYLINES["prepared_meeting_ids"]) == {
        "meeting-atlas-engineering-sync",
        "meeting-northstar-escalation-review",
        "meeting-atlas-launch-readiness",
    }
    assert set(STORYLINES["prepared_meeting_ids"]).issubset(meeting_ids)
    assert all(services.workspace.meetings[meeting_id].preparation_eligibility == "eligible" for meeting_id in STORYLINES["prepared_meeting_ids"])
