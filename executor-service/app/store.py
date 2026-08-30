from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from threading import RLock

from .models import ActionCommand, ClaimedCommand, CommandAttempt


class CommandStore(ABC):
    @abstractmethod
    def claim(self, command_id: str, now: datetime, lease_seconds: int, max_attempts: int) -> ClaimedCommand: ...

    @abstractmethod
    def finish(self, command: ActionCommand, attempt: CommandAttempt) -> None: ...


def claim_command(command: ActionCommand, now: datetime, lease_seconds: int, max_attempts: int) -> ClaimedCommand:
    if command.status == "succeeded":
        return ClaimedCommand(command=command, execute=False, reason="already_succeeded")
    if command.status in {"rejected", "failed", "stale", "proposed"}:
        return ClaimedCommand(command=command, execute=False, reason="terminal")
    if command.status == "executing" and command.lease_expires_at and command.lease_expires_at > now:
        return ClaimedCommand(command=command, execute=False, reason="active_lease")
    if command.attempt_count >= max_attempts:
        command.status = "failed"
        command.error_code = "ATTEMPT_LIMIT"
        return ClaimedCommand(command=command, execute=False, reason="attempt_limit")
    command.status = "executing"
    command.attempt_count += 1
    command.lease_expires_at = now + timedelta(seconds=lease_seconds)
    command.error_code = None
    return ClaimedCommand(command=command, execute=True, reason="claimed")


class MemoryCommandStore(CommandStore):
    def __init__(self, commands: list[ActionCommand]):
        self.commands = {item.id: item for item in commands}
        self.attempts: dict[str, CommandAttempt] = {}
        self.lock = RLock()

    def claim(self, command_id: str, now: datetime, lease_seconds: int, max_attempts: int) -> ClaimedCommand:
        with self.lock:
            return claim_command(self.commands[command_id], now, lease_seconds, max_attempts)

    def finish(self, command: ActionCommand, attempt: CommandAttempt) -> None:
        with self.lock:
            self.commands[command.id] = command
            self.attempts[attempt.id] = attempt


class FirestoreCommandStore(CommandStore):
    def __init__(self, *, project_id: str, database: str, organization_id: str):
        from google.api_core.exceptions import AlreadyExists
        from google.cloud import firestore

        self.firestore = firestore
        self.already_exists = AlreadyExists
        self.client = firestore.Client(project=project_id, database=database)
        self.root = self.client.collection("organizations").document(organization_id)

    def claim(self, command_id: str, now: datetime, lease_seconds: int, max_attempts: int) -> ClaimedCommand:
        reference = self.root.collection("commands").document(command_id)
        transaction = self.client.transaction()

        @self.firestore.transactional
        def execute(txn):
            snapshot = reference.get(transaction=txn)
            if not snapshot.exists:
                raise KeyError(command_id)
            claimed = claim_command(ActionCommand.model_validate(snapshot.to_dict()), now, lease_seconds, max_attempts)
            txn.set(reference, claimed.command.model_dump(mode="json", exclude_none=True))
            return claimed

        return execute(transaction)

    def finish(self, command: ActionCommand, attempt: CommandAttempt) -> None:
        transaction = self.client.transaction()
        command_ref = self.root.collection("commands").document(command.id)
        attempt_ref = self.root.collection("command_attempts").document(attempt.id)
        mission_ref = self.root.collection("missions").document(command.mission_id)

        @self.firestore.transactional
        def persist(txn) -> None:
            mission_snapshot = mission_ref.get(transaction=txn) if command.status == "succeeded" else None
            txn.set(command_ref, command.model_dump(mode="json", exclude_none=True))
            # Deterministic attempt IDs make Pub/Sub redelivery immutable and idempotent.
            txn.create(attempt_ref, attempt.model_dump(mode="json", exclude_none=True))
            if mission_snapshot and mission_snapshot.exists:
                mission = mission_snapshot.to_dict()
                meeting_id = mission.get("meeting_id")
                if meeting_id:
                    confirmed = {
                        "calendar.cancel": "cancelled",
                        "calendar.shorten": "shortened",
                        "calendar.update_agenda": "agenda_updated",
                    }[command.command_type]
                    txn.set(
                        self.root.collection("meetings").document(str(meeting_id)),
                        {
                            "confirmed_action": confirmed,
                            "pending_action": "none",
                            "etag": command.applied_etag or command.expected_etag,
                        },
                        merge=True,
                    )

        try:
            persist(transaction)
        except self.already_exists:
            # The same finished attempt was already recorded before an HTTP retry.
            return
