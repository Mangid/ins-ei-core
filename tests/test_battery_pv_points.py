from datetime import datetime

from ins_ei.models import Point, Quality, Source
from ins_ei.point_registry import definition, validate_point
from ins_ei.state import StateStore


def test_battery_and_pv_points_have_control_freshness():
    assert definition("pv.generation_power").stale_after_seconds == 15
    assert definition("battery.soc").stale_after_seconds == 30
    assert definition("battery.charge_power").stale_after_seconds == 15


def test_battery_units_are_canonical():
    assert validate_point("battery.soc", 80.0, "%") == []
    assert validate_point("battery.energy_free", 6.5, "kWh") == []
    assert validate_point("battery.charge_power", 2500.0, "W") == []


def test_directional_battery_power_can_coexist():
    now = datetime.now().astimezone()
    store = StateStore()
    source = Source(plugin_instance="battery_io")
    store.ingest([
        Point(component_id="battery", point="battery.charge_power", value=1500.0, unit="W", quality=Quality.GOOD, observed_at=now, source=source),
        Point(component_id="battery", point="battery.discharge_power", value=0.0, unit="W", quality=Quality.GOOD, observed_at=now, source=source),
    ])
    assert store.get("battery", "battery.charge_power").value == 1500.0
    assert store.get("battery", "battery.discharge_power").value == 0.0
