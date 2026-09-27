from __future__ import annotations

from collections import defaultdict
from threading import RLock
from time import monotonic


class Metrics:
    def __init__(self) -> None:
        self._lock = RLock()
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self.started_monotonic = monotonic()

    def inc(self, name: str, amount: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += amount

    def set(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "uptime_seconds": max(0.0, monotonic() - self.started_monotonic),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
            }
