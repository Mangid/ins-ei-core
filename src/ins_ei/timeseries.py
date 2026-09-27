from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Any

from ins_ei.models import Quality


@dataclass(frozen=True)
class TimeSlot:
    series: str
    start: datetime
    end: datetime
    value: float
    unit: str
    quality: Quality = Quality.GOOD
    generated_at: datetime | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = None

    def validate(self) -> None:
        if self.end <= self.start:
            raise ValueError("TIMESLOT_END_BEFORE_START")
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("TIMESLOT_TIMEZONE_REQUIRED")
        if self.generated_at is not None and self.generated_at.tzinfo is None:
            raise ValueError("TIMESLOT_GENERATED_AT_TIMEZONE_REQUIRED")


class TimeSeriesStore:
    """Thread-safe timestamped slot store for market/forecast data."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._series: dict[str, list[TimeSlot]] = {}

    def replace(self, series: str, slots: list[TimeSlot]) -> None:
        for slot in slots:
            slot.validate()
            if slot.series != series:
                raise ValueError(f"TIMESLOT_SERIES_MISMATCH:{slot.series}:{series}")
        ordered = sorted(slots, key=lambda s: s.start)
        for previous, current in zip(ordered, ordered[1:]):
            if current.start < previous.end:
                raise ValueError(f"TIMESLOT_OVERLAP:{series}")
        with self._lock:
            self._series[series] = ordered

    def series(self, series: str) -> list[TimeSlot]:
        with self._lock:
            return list(self._series.get(series, []))

    def current(self, series: str, now: datetime | None = None) -> TimeSlot | None:
        now = now or datetime.now().astimezone()
        with self._lock:
            for slot in self._series.get(series, []):
                if slot.start <= now < slot.end:
                    return slot
        return None

    def window(self, series: str, start: datetime, end: datetime) -> list[TimeSlot]:
        with self._lock:
            return [
                slot for slot in self._series.get(series, [])
                if slot.end > start and slot.start < end
            ]

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._series)
