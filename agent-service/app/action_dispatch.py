from __future__ import annotations

import json
from typing import Protocol


class ActionPublisher(Protocol):
    def publish(self, command_id: str) -> str: ...


class NullActionPublisher:
    def publish(self, command_id: str) -> str:
        return f"local:{command_id}"


class DisabledActionPublisher:
    def publish(self, command_id: str) -> str:
        raise RuntimeError("Action dispatch is not configured")


class GooglePubSubActionPublisher:
    def __init__(self, *, project_id: str, topic_id: str):
        if not project_id or not topic_id:
            raise ValueError("Project and command topic are required")
        try:
            from google.cloud import pubsub_v1  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - deployment-only path
            raise RuntimeError("Install noping-agent-service[google] for Pub/Sub command dispatch") from exc
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_id)

    def publish(self, command_id: str) -> str:
        payload = json.dumps({"schema_version": "1", "command_id": command_id}, separators=(",", ":")).encode()
        return self.publisher.publish(self.topic_path, payload, command_id=command_id).result(timeout=10)
