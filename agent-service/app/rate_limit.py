from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock


class RateLimitExceeded(RuntimeError):
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class RateLimiter:
    def __init__(self, settings, now_fn):
        self.settings = settings
        self.now_fn = now_fn
        self.lock = Lock()
        self.user_events: dict[str, deque[datetime]] = defaultdict(deque)
        self.org_events: deque[datetime] = deque()
        self.active_runs = 0

    @staticmethod
    def _trim(queue: deque[datetime], cutoff: datetime) -> None:
        while queue and queue[0] < cutoff:
            queue.popleft()

    def acquire(self, user_id: str) -> None:
        now = self.now_fn()
        with self.lock:
            user = self.user_events[user_id]
            self._trim(user, now - timedelta(days=1))
            self._trim(self.org_events, now - timedelta(days=1))
            minute_user = sum(item >= now - timedelta(minutes=1) for item in user)
            hour_user = sum(item >= now - timedelta(hours=1) for item in user)
            minute_org = sum(item >= now - timedelta(minutes=1) for item in self.org_events)
            if minute_user >= self.settings.max_user_per_minute:
                raise RateLimitExceeded("Per-user minute limit reached")
            if hour_user >= self.settings.max_user_per_hour:
                raise RateLimitExceeded("Per-user hourly limit reached", 3600)
            if len(user) >= self.settings.max_user_per_day:
                raise RateLimitExceeded("Per-user daily limit reached", 86400)
            if minute_org >= self.settings.max_org_per_minute:
                raise RateLimitExceeded("Organization minute limit reached")
            if len(self.org_events) >= self.settings.max_org_per_day:
                raise RateLimitExceeded("Organization daily limit reached", 86400)
            if self.active_runs >= self.settings.max_concurrent_runs:
                raise RateLimitExceeded("Concurrent run limit reached", 5)
            user.append(now)
            self.org_events.append(now)
            self.active_runs += 1

    def release(self) -> None:
        with self.lock:
            self.active_runs = max(0, self.active_runs - 1)

    def reset(self) -> None:
        """Clear counters only for an explicit demo reset."""
        with self.lock:
            self.user_events.clear()
            self.org_events.clear()
            self.active_runs = 0
