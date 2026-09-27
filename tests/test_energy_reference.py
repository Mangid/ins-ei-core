from ins_ei.plugins.energy_reference import EnergyReferencePlugin
from ins_ei.point_registry import validate_point


def test_reference_plugin_proves_pv_battery_contract():
    plugin = EnergyReferencePlugin("energy_io", {
        "pv_component": "pv",
        "battery_component": "battery",
        "values": {"pv_generation_w": 7000, "soc_percent": 80},
    })
    plugin.validate_config()
    plugin.start()
    points = plugin.read_points()
    values = {(p.component_id, p.point): p.value for p in points}
    assert values[("pv", "pv.generation_power")] == 7000
    assert values[("battery", "battery.soc")] == 80
    for point in points:
        assert validate_point(point.point, point.value, point.unit) == []
