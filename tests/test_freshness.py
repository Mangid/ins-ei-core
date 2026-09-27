from datetime import datetime, timedelta

from ins_ei.models import Point, Quality, Source
from ins_ei.state import StateStore


def point(age_seconds: float, quality=Quality.GOOD):
    return Point(
        component_id="grid",
        point="grid.export_power",
        value=1000,
        unit="W",
        quality=quality,
        observed_at=datetime.now().astimezone() - timedelta(seconds=age_seconds),
        source=Source(plugin_instance="meter"),
    )


def test_good_point_becomes_stale_after_default_threshold():
    store = StateStore(default_stale_after_seconds=60)
    store.ingest([point(90)])
    assert store.get("grid", "grid.export_power").quality == Quality.STALE


def test_fresh_point_remains_good():
    store = StateStore(default_stale_after_seconds=60)
    store.ingest([point(10)])
    assert store.get("grid", "grid.export_power").quality == Quality.GOOD


def test_per_point_threshold_overrides_default():
    store = StateStore(default_stale_after_seconds=120)
    store.set_stale_threshold("grid", "grid.export_power", 5)
    store.ingest([point(10)])
    assert store.get("grid", "grid.export_power").quality == Quality.STALE


def test_existing_invalid_quality_is_not_rewritten():
    store = StateStore(default_stale_after_seconds=1)
    store.ingest([point(100, Quality.INVALID)])
    assert store.get("grid", "grid.export_power").quality == Quality.INVALID
