from datetime import datetime, timedelta, timezone

import pytest

from ins_ei.models import Quality
from ins_ei.timeseries import TimeSeriesStore, TimeSlot


def slot(series, start, value, hours=1):
    return TimeSlot(
        series=series,
        start=start,
        end=start + timedelta(hours=hours),
        value=value,
        unit="ct/kWh",
        quality=Quality.GOOD,
        generated_at=start - timedelta(minutes=5),
        source="test",
    )


def test_current_slot_and_window():
    start = datetime(2026, 9, 27, 10, tzinfo=timezone.utc)
    store = TimeSeriesStore()
    store.replace("market.import_price", [
        slot("market.import_price", start, 10),
        slot("market.import_price", start + timedelta(hours=1), 20),
    ])
    assert store.current("market.import_price", start + timedelta(minutes=30)).value == 10
    assert len(store.window("market.import_price", start, start + timedelta(hours=2))) == 2


def test_overlapping_slots_are_rejected():
    start = datetime(2026, 9, 27, 10, tzinfo=timezone.utc)
    store = TimeSeriesStore()
    with pytest.raises(ValueError, match="TIMESLOT_OVERLAP"):
        store.replace("forecast.pv_energy", [
            TimeSlot("forecast.pv_energy", start, start + timedelta(hours=2), 1, "kWh"),
            TimeSlot("forecast.pv_energy", start + timedelta(hours=1), start + timedelta(hours=3), 2, "kWh"),
        ])


def test_timezone_is_required():
    start = datetime(2026, 9, 27, 10)
    with pytest.raises(ValueError, match="TIMESLOT_TIMEZONE_REQUIRED"):
        TimeSlot("x", start, start + timedelta(hours=1), 1, "kWh").validate()
