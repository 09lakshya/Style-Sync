"""Slow down password guessing on /auth/login.

Failures are counted per (email, client address) in memory. After
MAX_FAILURES inside WINDOW_SECONDS, further attempts for that pair are refused
with 429 until the oldest failure ages out; a successful login clears the
count. In-memory means per process and reset on restart - enough for one API
process. Several workers or hosts would need a shared store such as Redis.
"""

import time
from collections import deque

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60


class LoginRateLimiter:
    def __init__(self, max_failures: int = MAX_FAILURES, window_seconds: float = WINDOW_SECONDS) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[tuple[str, str], deque[float]] = {}

    @staticmethod
    def _key(email: str, client: str) -> tuple[str, str]:
        return (email.strip().lower(), client)

    def _recent(self, key: tuple[str, str], now: float) -> deque[float]:
        failures = self._failures.get(key)
        if failures is None:
            return deque()
        while failures and now - failures[0] >= self.window_seconds:
            failures.popleft()
        if not failures:
            self._failures.pop(key, None)
        return failures

    def retry_after(self, email: str, client: str, now: float | None = None) -> int:
        """Seconds until another attempt is allowed; 0 when it is allowed now."""
        now = time.monotonic() if now is None else now
        failures = self._recent(self._key(email, client), now)
        if len(failures) < self.max_failures:
            return 0
        return max(1, int(self.window_seconds - (now - failures[0])) + 1)

    def record_failure(self, email: str, client: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        key = self._key(email, client)
        self._recent(key, now)
        self._failures.setdefault(key, deque()).append(now)

    def reset(self, email: str, client: str) -> None:
        self._failures.pop(self._key(email, client), None)


login_rate_limiter = LoginRateLimiter()
