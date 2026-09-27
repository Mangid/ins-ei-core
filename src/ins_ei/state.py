from __future__ import annotations

from datetime import datetime
from threading import RLock

from .models import Point, Quality


class StateStore:
    def __init__(self, default_stale_after_seconds: float = 120.0) -> None:
        self._points: dict[tuple[str, str], Point] = {}
        self._lock = RLock()
        self.default_stale_after_seconds = float(default_stale_after_seconds)
        self._stale_thresholds: dict[tuple[str, str], float] = {}

    def ingest(self, points: list[Point]) -> None:
        with self._lock:
            for point in points:
                self._points[(point.component_id, point.point)] = point

    def set_stale_threshold(self, component_id: str, point: str, seconds: float) -> None:
        if seconds <= 0:
            raise ValueError("STALE_THRESHOLD_MUST_BE_POSITIVE")
        with self._lock:
            self._stale_thresholds[(component_id, point)] = float(seconds)

    def stale_after_seconds(self, component_id: str, point: str) -> float:
        return self._stale_thresholds.get(
            (component_id, point), self.default_stale_after_seconds
        )

    @staticmethod
    def age_seconds(point: Point, now: datetime | None = None) -> float:
        now = now or datetime.now().astimezone()
        observed = point.observed_at
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=now.tzinfo)
        return max(0.0, (now - observed).total_seconds())

    def get_raw(self, component_id: str, point: str) -> Point | None:
        with self._lock:
            return self._points.get((component_id, point))

    def get(self, component_id: str, point: str, now: datetime | None = None) -> Point | None:
        with self._lock:
            stored = self._points.get((component_id, point))
            if stored is None:
                return None
            threshold = self.stale_after_seconds(component_id, point)
            if stored.quality == Quality.GOOD and self.age_seconds(stored, now) > threshold:
                return stored.model_copy(update={"quality": Quality.STALE})
            return stored

    def snapshot(self, now: datetime | None = None) -> list[Point]:
        with self._lock:
            keys = list(self._points)
        return [self.get(component, point, now) for component, point in keys]
