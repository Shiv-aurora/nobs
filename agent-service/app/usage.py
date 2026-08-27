from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from uuid import uuid4

from .workspace import Workspace


class ModelBudgetExceeded(RuntimeError):
    def __init__(self, reason: str, *, retry_after: int = 3600):
        super().__init__(reason)
        self.reason = reason
        self.retry_after = retry_after


@dataclass(frozen=True)
class ModelUsage:
    model_name: str
    calls: int = 1
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0


@dataclass(frozen=True)
class BudgetReservation:
    id: str
    calls: int
    input_tokens: int
    output_tokens: int


def estimate_tokens(value: str) -> int:
    """Conservative token estimate used before a paid model call.

    English prose often averages roughly four characters per token. NoPing uses
    three characters per token plus a small floor so the preflight check errs on
    the side of blocking rather than overspending.
    """

    return max(1, math.ceil(len(value) / 3))


class ModelUsageGuard:
    """Single-instance hard guard for model calls and token consumption.

    Cloud Run is capped at one instance for the hackathon profile, so this
    process-level lock provides an atomic admission gate. Totals are also stored
    through Workspace so Firestore restores the conservative counters after a
    restart. Reservations are charged before the call; a crash can therefore
    only over-count usage, never hide spend.
    """

    def __init__(
        self,
        workspace: Workspace,
        now_fn,
        *,
        max_calls_per_query: int,
        max_input_tokens_per_query: int,
        max_output_tokens_per_query: int,
        max_calls_per_day: int,
        max_input_tokens_per_day: int,
        max_output_tokens_per_day: int,
    ) -> None:
        self.workspace = workspace
        self.now_fn = now_fn
        self.max_calls_per_query = max_calls_per_query
        self.max_input_tokens_per_query = max_input_tokens_per_query
        self.max_output_tokens_per_query = max_output_tokens_per_query
        self.max_calls_per_day = max_calls_per_day
        self.max_input_tokens_per_day = max_input_tokens_per_day
        self.max_output_tokens_per_day = max_output_tokens_per_day
        self._lock = RLock()
        self._reservations: dict[str, BudgetReservation] = {}

    def _day_key(self, now: datetime) -> int:
        return int(now.strftime("%Y%m%d"))

    def _normalize_day(self, now: datetime) -> None:
        current = self._day_key(now)
        if self.workspace.stats.get("model_usage_day") == current:
            return
        with self.workspace.lock:
            self.workspace.stats.update(
                {
                    "model_usage_day": current,
                    "model_calls": 0,
                    "model_input_tokens": 0,
                    "model_output_tokens": 0,
                    "model_cached_input_tokens": 0,
                    "model_budget_blocks": 0,
                }
            )
        self.workspace.persist_stats()

    def reserve(self, *, calls: int, input_tokens: int, output_tokens: int) -> BudgetReservation:
        with self._lock:
            self._normalize_day(self.now_fn())
            self._check_query_limits(calls=calls, input_tokens=input_tokens, output_tokens=output_tokens)
            self._check_daily_limits(calls=calls, input_tokens=input_tokens, output_tokens=output_tokens)
            reservation = BudgetReservation(
                id=f"budget-{uuid4().hex[:12]}",
                calls=calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            self._reservations[reservation.id] = reservation
            self._adjust(calls=calls, input_tokens=input_tokens, output_tokens=output_tokens)
            return reservation

    def finalize(self, reservation: BudgetReservation, usage: ModelUsage) -> None:
        with self._lock:
            reserved = self._reservations.pop(reservation.id, None)
            if reserved is None:
                return
            self._adjust(
                calls=usage.calls - reserved.calls,
                input_tokens=usage.input_tokens - reserved.input_tokens,
                output_tokens=usage.output_tokens - reserved.output_tokens,
                cached_input_tokens=usage.cached_input_tokens,
            )

    def cancel(self, reservation: BudgetReservation) -> None:
        with self._lock:
            reserved = self._reservations.pop(reservation.id, None)
            if reserved is None:
                return
            self._adjust(
                calls=-reserved.calls,
                input_tokens=-reserved.input_tokens,
                output_tokens=-reserved.output_tokens,
            )

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            self._normalize_day(self.now_fn())
            keys = (
                "model_usage_day",
                "model_calls",
                "model_input_tokens",
                "model_output_tokens",
                "model_cached_input_tokens",
                "model_budget_blocks",
            )
            with self.workspace.lock:
                return {key: int(self.workspace.stats.get(key, 0)) for key in keys}

    def reset(self) -> None:
        with self._lock:
            self._reservations.clear()
            with self.workspace.lock:
                self.workspace.stats.update(
                    {
                        "model_usage_day": self._day_key(self.now_fn()),
                        "model_calls": 0,
                        "model_input_tokens": 0,
                        "model_output_tokens": 0,
                        "model_cached_input_tokens": 0,
                        "model_budget_blocks": 0,
                    }
                )
            self.workspace.persist_stats()

    def _check_query_limits(self, *, calls: int, input_tokens: int, output_tokens: int) -> None:
        checks = (
            (calls > self.max_calls_per_query, "Model-call limit exceeded for this query."),
            (input_tokens > self.max_input_tokens_per_query, "Input-token limit exceeded for this query."),
            (output_tokens > self.max_output_tokens_per_query, "Output-token limit exceeded for this query."),
        )
        for blocked, reason in checks:
            if blocked:
                self._record_block()
                raise ModelBudgetExceeded(reason)

    def _check_daily_limits(self, *, calls: int, input_tokens: int, output_tokens: int) -> None:
        checks = (
            (self.workspace.stats.get("model_calls", 0) + calls > self.max_calls_per_day, "Daily model-call budget exhausted."),
            (
                self.workspace.stats.get("model_input_tokens", 0) + input_tokens > self.max_input_tokens_per_day,
                "Daily model input-token budget exhausted.",
            ),
            (
                self.workspace.stats.get("model_output_tokens", 0) + output_tokens > self.max_output_tokens_per_day,
                "Daily model output-token budget exhausted.",
            ),
        )
        for blocked, reason in checks:
            if blocked:
                self._record_block()
                raise ModelBudgetExceeded(reason, retry_after=86400)

    def _record_block(self) -> None:
        with self.workspace.lock:
            self.workspace.stats["model_budget_blocks"] = self.workspace.stats.get("model_budget_blocks", 0) + 1
        self.workspace.persist_stats()

    def _adjust(
        self,
        *,
        calls: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_input_tokens: int = 0,
    ) -> None:
        with self.workspace.lock:
            for key, delta in (
                ("model_calls", calls),
                ("model_input_tokens", input_tokens),
                ("model_output_tokens", output_tokens),
                ("model_cached_input_tokens", cached_input_tokens),
            ):
                self.workspace.stats[key] = max(0, self.workspace.stats.get(key, 0) + delta)
        self.workspace.persist_stats()
