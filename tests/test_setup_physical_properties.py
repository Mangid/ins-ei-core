from pathlib import Path

def test_setup_configures_four_canonical_buffer_sensor_positions():
    src=Path("src/ins_ei/setup_web.py").read_text()
    assert "temperature_sensor_positions" in src
    assert 'sensorRow(\'TOP\',\'Fühlerposition 1 · TOP\')' in src
    assert 'sensorRow(\'UPPER_MIDDLE\',\'Fühlerposition 2 · UPPER MIDDLE\')' in src
    assert 'sensorRow(\'LOWER_MIDDLE\',\'Fühlerposition 3 · LOWER MIDDLE\')' in src
    assert 'sensorRow(\'BOTTOM\',\'Fühlerposition 4 · BOTTOM\')' in src
    assert "– nicht vorhanden –" in src
    assert 'data-component-prop="temperature_sensor_count"' not in src
    assert 'data-component-text-prop="temperature_sensor_layout"' not in src

def test_physical_storage_and_generator_metadata_remain_installation_specific():
    src=Path("src/ins_ei/setup_web.py").read_text()
    assert 'data-component-prop="volume_l"' in src
    assert 'data-component-prop="nominal_power_kw"' in src
    assert "x.kind==='HEAT_GENERATOR'" in src
