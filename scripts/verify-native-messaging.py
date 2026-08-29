#!/usr/bin/env python3
"""Exercise NoPing's native Mattermost message hooks against a running stack."""

from __future__ import annotations

import atexit
import json
import os
import time
import urllib.error
import urllib.request


BASE_URL = os.environ.get("MATTERMOST_URL", "http://localhost:8065").rstrip("/")
PASSWORD = os.environ.get("NOPING_DEMO_USER_PASSWORD", "NoPing-Demo-2026!")
PLUGIN_API = "/plugins/com.noping.enterprise/api/v1"
CREATED_POST_IDS: list[str] = []


class Session:
    def __init__(self, username: str, password: str = PASSWORD) -> None:
        request = urllib.request.Request(
            f"{BASE_URL}/api/v4/users/login",
            data=json.dumps({"login_id": username, "password": password}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            self.user = json.load(response)
            self.token = response.headers["Token"]

    def request(self, method: str, path: str, payload: object | None = None) -> object:
        body = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=body,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
            return json.loads(data) if data else {}


def channel(session: Session, team: str, name: str) -> dict[str, object]:
    return session.request("GET", f"/api/v4/teams/name/{team}/channels/name/{name}")  # type: ignore[return-value]


def create_post(session: Session, channel_id: str, message: str) -> dict[str, object]:
    post = session.request("POST", "/api/v4/posts", {
        "channel_id": channel_id,
        "message": message,
        "props": {"noping_verification": True},
    })  # type: ignore[assignment]
    CREATED_POST_IDS.append(str(post["id"]))  # type: ignore[index]
    return post  # type: ignore[return-value]


def cleanup_verification_posts() -> None:
    if not CREATED_POST_IDS:
        return
    admin_password = os.environ.get("MATTERMOST_ADMIN_PASSWORD", "")
    if not admin_password:
        return
    try:
        admin = Session(os.environ.get("MATTERMOST_ADMIN_USERNAME", "admin"), admin_password)
    except Exception:
        return
    for post_id in CREATED_POST_IDS:
        try:
            admin.request("DELETE", f"/api/v4/posts/{post_id}")
        except Exception:
            pass


atexit.register(cleanup_verification_posts)


def agent_replies(session: Session, source_id: str) -> list[dict[str, object]]:
    thread = session.request("GET", f"/api/v4/posts/{source_id}/thread")
    posts = thread["posts"]  # type: ignore[index]
    return [post for post in posts.values() if post.get("props", {}).get("noping_source_post_id") == source_id]


def wait_for_final(session: Session, source_id: str, timeout: float = 45) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    last: dict[str, object] | None = None
    while time.monotonic() < deadline:
        replies = agent_replies(session, source_id)
        if len(replies) > 1:
            raise AssertionError(f"source {source_id} produced {len(replies)} agent posts")
        if replies:
            last = replies[0]
            state = last.get("props", {}).get("noping_state")  # type: ignore[union-attr]
            if state in {"answered", "escalated", "refused", "failed"}:
                return last
        time.sleep(0.4)
    raise AssertionError(f"agent reply did not finish; last={last}")


def assert_no_reply(session: Session, source_id: str) -> None:
    time.sleep(1.2)
    assert agent_replies(session, source_id) == [], f"unexpected delegate reply for {source_id}"


def main() -> None:
    maya = Session("maya")
    daniel = Session("daniel")
    priya = Session("priya")
    sarah = Session("sarah")
    atlas = channel(maya, "acme", "project-atlas")
    channel_id = str(atlas["id"])
    maya.request("POST", f"{PLUGIN_API}/demo/reset", {})

    routine = create_post(maya, channel_id, f"Native status note with no answer requested {time.time_ns()}")
    assert_no_reply(maya, str(routine["id"]))

    before = maya.request("GET", f"{PLUGIN_API}/metrics")
    direct = create_post(maya, channel_id, f" --direct @sarah Human judgment only {time.time_ns()}")
    assert str(direct["message"]).startswith("@sarah Human judgment only")
    assert direct.get("props", {}).get("noping_delivery_mode") == "human_only"
    assert_no_reply(maya, str(direct["id"]))
    after = maya.request("GET", f"{PLUGIN_API}/metrics")
    assert after["model_calls"] == before["model_calls"]  # type: ignore[index]

    broadcast = create_post(maya, channel_id, f"@channel routine update {time.time_ns()}")
    assert_no_reply(maya, str(broadcast["id"]))

    organization = create_post(maya, channel_id, f"Why is Atlas delayed? {time.time_ns()}")
    org_reply = wait_for_final(maya, str(organization["id"]))
    org_props = org_reply["props"]
    assert org_props["noping_agent_kind"] == "organization"  # type: ignore[index]
    assert int(org_props["noping_agents_consulted"]) == 4  # type: ignore[index]
    assert org_props["noping_route"] == (  # type: ignore[index]
        "Project Atlas Delegate → Engineering Delegate → Sarah Chen Delegate → Security Delegate"
    )
    assert org_props["noping_people_interrupted"] == 0  # type: ignore[index]

    personal = create_post(daniel, channel_id, f"What is blocking Atlas security? {time.time_ns()}")
    personal_reply = wait_for_final(daniel, str(personal["id"]))
    personal_props = personal_reply["props"]
    assert personal_props["noping_agent_kind"] == "personal"  # type: ignore[index]
    assert personal_props["noping_represented_user_name"] == "Sarah Chen"  # type: ignore[index]

    coordinated = create_post(priya, channel_id, f"@sarah @daniel coordinate the Atlas blockers {time.time_ns()}")
    coordinated_reply = wait_for_final(priya, str(coordinated["id"]))
    assert coordinated_reply["props"]["noping_agent_kind"] == "organization"  # type: ignore[index]

    direct_channel = maya.request("POST", "/api/v4/channels/direct", [maya.user["id"], sarah.user["id"]])
    dm = create_post(maya, str(direct_channel["id"]), f"What is your Atlas availability? {time.time_ns()}")  # type: ignore[index]
    dm_reply = wait_for_final(maya, str(dm["id"]))
    assert dm_reply["props"]["noping_represented_user_name"] == "Sarah Chen"  # type: ignore[index]

    denied = create_post(maya, channel_id, f"What is Sarah's salary? {time.time_ns()}")
    denied_reply = wait_for_final(maya, str(denied["id"]))
    assert denied_reply["props"]["noping_security_state"] == "denied"  # type: ignore[index]
    assert denied_reply["props"]["noping_represented_user_name"] == "Sarah Chen"  # type: ignore[index]

    print("Native messaging integration passed: routine chatter ignored; untagged organization/personal scope, human-only, coordinated, DM, and security flows passed.")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        raise SystemExit(f"HTTP {error.code}: {error.read().decode(errors='replace')}") from error
