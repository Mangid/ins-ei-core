from datetime import datetime

from ins_ei.plugins.victron_gx import VictronGXPlugin


def test_victron_battery_power_is_directional():
    p = VictronGXPlugin("gx", {"host": "x", "portal_id": "id", "battery_component": "battery", "pv_component": "pv"})
    now = datetime.now().astimezone()
    p.values = {
        "N/id/system/0/Dc/Battery/Soc": (80, now),
        "N/id/system/0/Dc/Battery/Power": (-2100, now),
        "N/id/system/0/Dc/Pv/Power": (5400, now),
    }
    values = {x.point: x.value for x in p.read_points()}
    assert values["battery.soc"] == 80
    assert values["battery.charge_power"] == 0
    assert values["battery.discharge_power"] == 2100
    assert values["pv.generation_power"] == 5400
