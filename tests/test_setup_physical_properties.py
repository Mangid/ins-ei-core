from pathlib import Path

def test_setup_configures_four_canonical_buffer_sensor_positions():
    src=Path("src/ins_ei/setup_web.py").read_text()
    assert "temperature_sensor_positions" in src
    for pos in ("TOP","UPPER_MIDDLE","LOWER_MIDDLE","BOTTOM"):
        assert "data-buffer-sensor-pos=\\\"'+pos+'\\\"" in src
    assert "– nicht vorhanden –" in src
    assert 'data-component-prop="temperature_sensor_count"' not in src
    assert 'data-component-text-prop="temperature_sensor_layout"' not in src

def test_physical_storage_and_generator_metadata_remain_installation_specific():
    src=Path("src/ins_ei/setup_web.py").read_text()
    assert 'data-component-prop="volume_l"' in src
    assert 'data-component-prop="nominal_power_kw"' in src
    assert "x.kind==='HEAT_GENERATOR'" in src
