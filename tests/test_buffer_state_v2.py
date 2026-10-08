from pathlib import Path

def test_buffer_state_v2_uses_topology_drivers_and_all_observed_positions():
    src=Path("src/ins_ei/learning_coordinator.py").read_text()
    assert "def fit_buffer_state_v2" in src
    assert '"POWER_TO_HEAT"' in src
    assert '"HEAT_GENERATOR"' in src
    assert '"HEATING_CIRCUIT", "DHW"' in src
    assert 'item["sensor_rates"].setdefault(position, []).append' in src
    assert 'model.metadata["buffer_state_v2_fit"] = result' in src
    assert 'model.metadata["phase"] = "BUFFER_STATE_V2_1"' in src
