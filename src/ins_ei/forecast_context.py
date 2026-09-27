from __future__ import annotations

from datetime import datetime, timedelta

from ins_ei.timeseries import TimeSeriesStore


class ForecastContext:
    def __init__(self, store: TimeSeriesStore, now: datetime | None = None) -> None:
        self.store = store
        self.now = now or datetime.now().astimezone()

    def current_value(self, series: str):
        slot = self.store.current(series, self.now)
        return None if slot is None else slot.value

    def next_hours(self, series: str, hours: int):
        return self.store.window(
            series,
            self.now,
            self.now + timedelta(hours=hours),
        )
