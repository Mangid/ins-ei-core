from datetime import datetime, timedelta

from ins_ei.historian import Historian
from ins_ei.models import Point, Quality, Source
from ins_ei.outcomes import OutcomeExpectation, OutcomeTracker
from ins_ei.state import StateStore


def put(store, value, observed_at):
    store.ingest([Point(
        component_id="buffer",
        point="thermal.temperature_upper",
        value=float(value),
        unit="°C",
        quality=Quality.GOOD,
        observed_at=observed_at,
        source=Source(plugin_instance="sensor"),
    )])


def test_outcome_tracks_expected_delta_and_residual(tmp_path):
    now = datetime.now().astimezone()
    state = StateStore(default_stale_after_seconds=10000)
    put(state, 50, now)
    historian = Historian(tmp_path / "h.db")
    tracker = OutcomeTracker(state, historian, "site", "site-v1")

    tracker.register(OutcomeExpectation(
        correlation_id="abc",
        metric_component="buffer",
        metric_point="thermal.temperature_upper",
        horizon_seconds=3600,
        expected_delta=7,
        tolerance=1.5,
        unit="°C",
        model_id="buffer_thermal",
        model_version="1",
    ), now)

    put(state, 55.8, now + timedelta(hours=1))
    results = tracker.evaluate_due(now + timedelta(hours=1))
    assert results[0].expected_value == 57
    assert round(results[0].residual, 1) == -1.2
    assert results[0].within_tolerance is True

    trace = historian.correlation("site", "abc")
    assert len(trace["events"]) == 2


def test_stale_outcome_is_unobservable(tmp_path):
    now = datetime.now().astimezone()
    state = StateStore(default_stale_after_seconds=10)
    state.set_stale_threshold("buffer", "thermal.temperature_upper", 10)
    put(state, 50, now)
    historian = Historian(tmp_path / "h.db")
    tracker = OutcomeTracker(state, historian, "site")
    tracker.register(OutcomeExpectation(
        correlation_id="x",
        metric_component="buffer",
        metric_point="thermal.temperature_upper",
        horizon_seconds=60,
        expected_value=55,
    ), now)
    result = tracker.evaluate_due(now + timedelta(seconds=61))[0]
    assert result.status == "UNOBSERVABLE"
