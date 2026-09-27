from ins_ei.plugins.mypv import MyPVPlugin


def test_mypv_normalizes_power_and_three_phase_telemetry():
    plugin = MyPVPlugin("mypv_main", {"host": "127.0.0.1", "component_id": "heater"})
    raw = {
        "device_power_w": 4321,
        "max_possible_power_w": 9000,
        "voltage_l1_v": 231,
        "current_l1_a": 6.2,
        "operation_state": 3,
        "solar_power_w": 5000,
        "http": {"device": "AC-THOR 9s", "fwversion": "x"},
    }

    points = plugin._normalize(raw)
    values = {(p.component_id, p.point): p.value for p in points}

    assert values[("heater", "power.electrical")] == 4321
    assert values[("heater", "power.maximum_available")] == 9000
    assert values[("heater", "electrical.voltage_l1")] == 231
    assert values[("heater", "state.operating")] == 3

    unmapped = plugin._unmapped(raw)
    assert unmapped["solar_power_w"] == 5000
    assert unmapped["http.device"] == "AC-THOR 9s"


def test_mypv_control_is_not_guessed():
    plugin = MyPVPlugin("mypv_main", {"host": "127.0.0.1"})
    try:
        plugin.execute("power_to_heat.set_power", {"power_w": 3000})
    except NotImplementedError:
        pass
    else:
        raise AssertionError("control must remain disabled until write interface is proven")
