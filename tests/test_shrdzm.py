from ins_ei.plugins.shrdzm import ShrdzmPlugin
from ins_ei.plugins.shrdzm_transport import ShrdzmTransport


def test_shrdzm_low_word_first_u32():
    words = [0x5678, 0x1234]
    assert ShrdzmTransport.u32(words, 0) == 0x12345678


def test_grid_semantics_are_directional_and_non_negative():
    plugin = ShrdzmPlugin("grid_meter", {"host": "127.0.0.1", "component_id": "grid"})
    raw = {
        "power_import_w": 1234,
        "power_export_w": 0,
        "signed_power_w": 1234,
        "import_energy_kwh": 100.5,
        "export_energy_kwh": 20.25,
        "voltage_l1_v": 230.1,
        "voltage_l2_v": 231.2,
        "voltage_l3_v": 229.9,
        "current_l1_a": 2.1,
        "current_l2_a": 1.9,
        "current_l3_a": 2.0,
        "reactive_power_import_var": 0,
        "reactive_power_export_var": 0,
    }
    points = plugin._normalize(raw)
    values = {p.point: p.value for p in points}
    assert values["grid.import_power"] == 1234
    assert values["grid.export_power"] == 0
    assert values["energy.import_total"] == 100.5


def test_export_is_not_encoded_as_negative_import():
    plugin = ShrdzmPlugin("grid_meter", {"host": "127.0.0.1"})
    raw = {
        "power_import_w": 0,
        "power_export_w": 2400,
        "signed_power_w": -2400,
        "import_energy_kwh": 1,
        "export_energy_kwh": 2,
        "voltage_l1_v": 230,
        "voltage_l2_v": 230,
        "voltage_l3_v": 230,
        "current_l1_a": 0,
        "current_l2_a": 0,
        "current_l3_a": 0,
        "reactive_power_import_var": 0,
        "reactive_power_export_var": 0,
    }
    values = {p.point: p.value for p in plugin._normalize(raw)}
    assert values["grid.import_power"] == 0
    assert values["grid.export_power"] == 2400
