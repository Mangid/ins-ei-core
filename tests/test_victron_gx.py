from ins_ei.plugins.victron_gx import VictronGXPlugin


class FakeTransport:
    @staticmethod
    def signed16(value):
        return value - 65536 if value > 32767 else value

    def read_registers(self, unit, address, count):
        if (unit, address, count) == (225, 259, 8):
            # 52.00 V, -40.0 A => -2080 W, 80 % SOC
            return [5200, 0, 65136, 250, 0, 0, 0, 800]
        if (unit, address, count) == (30, 2600, 3):
            return [100, 200, 300]
        if unit == 22 and count == 1:
            return {1029: [1800], 1033: [1800], 1037: [1800]}[address]
        raise AssertionError((unit, address, count))


def test_victron_battery_power_is_directional():
    p = VictronGXPlugin("gx", {
        "host": "x",
        "battery_component": "battery",
        "pv_component": "pv",
        "pv_unit_ids": [22],
    })
    p.transport = FakeTransport()
    p.running = True
    values = {x.point: x.value for x in p.read_points()}
    assert values["battery.soc"] == 80
    assert values["battery.charge_power"] == 0
    assert values["battery.discharge_power"] == 2080
    assert values["pv.generation_power"] == 5400
