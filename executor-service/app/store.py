from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import hashlib
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
    if command.expires_at <= now:
        command.status = "failed"
        command.error_code = "COMMAND_EXPIRED"
        return ClaimedCommand(command=command, execute=False, reason="expired")
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


def approval_state_is_valid(
    command: ActionCommand,
    mission: dict,
    calendar_checkpoint: dict,
    business_checkpoint: dict,
) -> bool:
    business_approver = business_checkpoint.get("resolved_by") if command.business_checkpoint_id else "not_required"
    expected_policy_hash = hashlib.sha256(
        f"{mission.get('policy_version', '')}:{mission.get('meeting_id', '')}:{business_approver}:{command.approved_by}".encode()
    ).hexdigest()
    business_approval_valid = (
        not command.business_checkpoint_id
        or (
            business_checkpoint.get("status") == "approved"
            and business_checkpoint.get("checkpoint_type") == "restricted_decision"
            and business_checkpoint.get("authority_type")
            and business_checkpoint.get("resolved_by") in business_checkpoint.get("authorized_actor_ids", [])
        )
    )
    return bool(
        mission.get("status") == "queued_action"
        and mission.get("calendar_checkpoint_id") == command.checkpoint_id
        and mission.get("business_checkpoint_id") == command.business_checkpoint_id
        and calendar_checkpoint.get("status") == "approved"
        and calendar_checkpoint.get("checkpoint_type") == "calendar_write"
        and calendar_checkpoint.get("resolved_by") == command.approved_by
        and command.approved_by in calendar_checkpoint.get("authorized_actor_ids", [])
        and command.id in calendar_checkpoint.get("command_ids", [])
        and business_approval_valid
        and command.approval_decision_id == (command.business_checkpoint_id or command.checkpoint_id)
        and command.policy_snapshot_hash == expected_policy_hash
    )


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
            command = ActionCommand.model_validate(snapshot.to_dict())
            mission_snapshot = self.root.collection("missions").document(command.mission_id).get(transaction=txn)
            checkpoint_snapshot = self.root.collection("human_checkpoints").document(command.checkpoint_id).get(transaction=txn)
            mission = mission_snapshot.to_dict() if mission_snapshot.exists else {}
            checkpoint = checkpoint_snapshot.to_dict() if checkpoint_snapshot.exists else {}
            business_checkpoint = {}
            if command.business_checkpoint_id:
                business_snapshot = self.root.collection("human_checkpoints").document(command.business_checkpoint_id).get(transaction=txn)
                business_checkpoint = business_snapshot.to_dict() if business_snapshot.exists else {}
            approval_valid = approval_state_is_valid(command, mission, checkpoint, business_checkpoint)
            if not approval_valid:
                command.status = "failed"
                command.error_code = "INVALID_APPROVAL_STATE"
                claimed = ClaimedCommand(command=command, execute=False, reason="invalid_approval")
            else:
                claimed = claim_command(command, now, lease_seconds, max_attempts)
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
            mission_snapshot = mission_ref.get(transaction=txn)
            txn.set(command_ref, command.model_dump(mode="json", exclude_none=True))
            # Deterministic attempt IDs make Pub/Sub redelivery immutable and idempotent.
            txn.create(attempt_ref, attempt.model_dump(mode="json", exclude_none=True))
            if mission_snapshot.exists:
                mission = mission_snapshot.to_dict()
                meeting_id = mission.get("meeting_id")
                completed_at = attempt.completed_at or attempt.started_at
                if command.status == "succeeded" and meeting_id:
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
                    proposed = [
                        command.model_dump(mode="json", exclude_none=True) if item.get("id") == command.id else item
                        for item in mission.get("proposed_commands", [])
                    ]
                    txn.set(
                        mission_ref,
                        {
                            "status": "completed",
                            "current_stage": "completed",
                            "completed_at": completed_at.isoformat(),
                            "updated_at": completed_at.isoformat(),
                            "proposed_commands": proposed,
                            "error_code": None,
                        },
                        merge=True,
                    )
                    result_step = {
                        "id": f"step-{command.mission_id}-result-verifier",
                        "mission_id": command.mission_id,
                        "ordinal": 9,
                        "node_id": "result-verifier",
                        "node_kind": "result_verifier",
                        "status": "completed",
                        "agent_version": "1.0.0",
                        "attempt": command.attempt_count,
                        "input_refs": [f"command:{command.id}"],
                        "output_refs": [f"provider-hash:{command.provider_response_hash}"],
                        "started_at": attempt.started_at.isoformat(),
                        "completed_at": completed_at.isoformat(),
                        "duration_ms": max(0.0, (completed_at - attempt.started_at).total_seconds() * 1000),
                    }
                    txn.set(self.root.collection("mission_steps").document(result_step["id"]), result_step)
                elif command.status in {"stale", "failed"}:
                    txn.set(
                        mission_ref,
                        {
                            "status": "failed",
                            "current_stage": "stale_input" if command.status == "stale" else "failed_safe",
                            "updated_at": completed_at.isoformat(),
                            "error_code": command.error_code,
                        },
                        merge=True,
                    )

        try:
            persist(transaction)
        except self.already_exists:
            # The same finished attempt was already recorded before an HTTP retry.
            return
