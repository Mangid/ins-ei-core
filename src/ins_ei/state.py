from __future__ import annotations

from threading import RLock

from .models import Point


class StateStore:
    def __init__(self) -> None:
        self._points: dict[tuple[str, str], Point] = {}
        self._lock = RLock()

    def ingest(self, points: list[Point]) -> None:
        with self._lock:
            for point in points:
                self._points[(point.component_id, point.point)] = point

    def get(self, component_id: str, point: str) -> Point | None:
        with self._lock:
            return self._points.get((component_id, point))

    def snapshot(self) -> list[Point]:
        with self._lock:
            return list(self._points.values())
