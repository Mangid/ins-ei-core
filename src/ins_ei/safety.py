from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import RLock


@dataclass(frozen=True)
class SafetyState:
    emergency_stop: bool
    reason: str | None
    changed_at: datetime


class SafetyController:
    """Central software safety gate for all INS-EI physical commands.

    This complements, but never replaces, required hardware safety devices.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._state = SafetyState(
            emergency_stop=False,
            reason=None,
            changed_at=datetime.now().astimezone(),
        )

    def state(self) -> SafetyState:
        with self._lock:
            return self._state

    def engage(self, reason: str) -> SafetyState:
        reason = reason.strip() or "manual emergency stop"
        with self._lock:
            self._state = SafetyState(
                emergency_stop=True,
                reason=reason,
                changed_at=datetime.now().astimezone(),
            )
            return self._state

    def release(self, reason: str = "manual reset") -> SafetyState:
        with self._lock:
            self._state = SafetyState(
                emergency_stop=False,
                reason=reason,
                changed_at=datetime.now().astimezone(),
            )
            return self._state

    def assert_command_allowed(self) -> None:
        state = self.state()
        if state.emergency_stop:
            raise RuntimeError(f"EMERGENCY_STOP_ACTIVE:{state.reason}")
