"""Google Workspace API Circuit Breaker conforming to [R-BAN-5]."""

from __future__ import annotations

import enum
import time
from typing import Any

from src.config import settings
from src.utils.deduplication import deduplicator
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CircuitState(enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class WorkspaceCircuitBreaker:
    """Protects Google Calendar & Tasks APIs from quota exhaustion and rate limit bans."""

    def __init__(
        self,
        error_threshold: int | None = None,
        cooldown_seconds: int | None = None,
    ) -> None:
        self.error_threshold = (
            error_threshold
            if error_threshold is not None
            else settings.circuit_breaker_error_threshold
        )
        self.cooldown_seconds = (
            cooldown_seconds
            if cooldown_seconds is not None
            else settings.circuit_breaker_cooldown_seconds
        )
        self._consecutive_errors: int = 0
        self._open_until: float = 0.0
        self._notified_owner: bool = False
        self._load_state()

    def _load_state(self) -> None:
        try:
            stored_until = deduplicator.meta_get("circuit_breaker_open_until")
            if stored_until:
                self._open_until = float(stored_until)
            stored_errs = deduplicator.meta_get("circuit_breaker_consecutive_errors")
            if stored_errs:
                self._consecutive_errors = int(stored_errs)
            stored_notified = deduplicator.meta_get("circuit_breaker_notified")
            if stored_notified:
                self._notified_owner = stored_notified == "1"
        except Exception as e:
            logger.debug("Failed to load circuit breaker state", error=str(e))

    def _persist_state(self) -> None:
        try:
            deduplicator.meta_set("circuit_breaker_open_until", str(self._open_until))
            deduplicator.meta_set(
                "circuit_breaker_consecutive_errors", str(self._consecutive_errors)
            )
            deduplicator.meta_set("circuit_breaker_notified", "1" if self._notified_owner else "0")
        except Exception as e:
            logger.debug("Failed to persist circuit breaker state", error=str(e))

    @property
    def state(self) -> CircuitState:
        now = time.time()
        if now < self._open_until:
            return CircuitState.OPEN
        if self._consecutive_errors >= self.error_threshold:
            return CircuitState.HALF_OPEN
        return CircuitState.CLOSED

    def can_execute(self) -> bool:
        """Returns True if writes are permitted; False if tripped."""
        current_state = self.state
        if current_state == CircuitState.OPEN:
            return False
        return True

    def record_success(self) -> None:
        """Record successful downstream API write and restore circuit to CLOSED."""
        self._consecutive_errors = 0
        self._open_until = 0.0
        self._notified_owner = False
        self._persist_state()

    def is_rate_limit_error(self, exc: Any) -> bool:
        """Determine whether the exception represents a 403 quota or 429 rate limit."""
        err_str = str(exc).lower()
        status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        if status_code in (403, 429):
            return True
        indicators = (
            "403",
            "429",
            "rate limit",
            "user rate limit",
            "rateLimitExceeded",
            "quotaExceeded",
            "too many requests",
        )
        return any(ind in err_str for ind in indicators)

    def record_error(self, exc: Any) -> bool:
        """Record error and trip if threshold reached.

        Returns True if newly tripped and owner should be notified.
        """
        if not self.is_rate_limit_error(exc):
            return False

        self._consecutive_errors += 1
        should_notify = False

        if self._consecutive_errors >= self.error_threshold:
            self._open_until = time.time() + self.cooldown_seconds
            if not self._notified_owner:
                self._notified_owner = True
                should_notify = True
            logger.warning(
                "Google Workspace Circuit Breaker TRIPPED",
                consecutive_errors=self._consecutive_errors,
                cooldown_seconds=self.cooldown_seconds,
            )

        self._persist_state()
        return should_notify


workspace_circuit_breaker = WorkspaceCircuitBreaker()
