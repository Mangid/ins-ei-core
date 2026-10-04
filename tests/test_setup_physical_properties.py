from pathlib import Path

def test_setup_captures_installation_specific_physical_properties():
    src=Path("src/ins_ei/setup_web.py").read_text()
    assert 'data-component-prop="volume_l"' in src
    assert 'data-component-prop="temperature_sensor_count"' in src
    assert 'data-component-text-prop="temperature_sensor_layout"' in src
    assert 'data-component-prop="nominal_power_kw"' in src
    assert "x.kind==='BUFFER' || x.kind==='DHW'" in src
    assert "x.kind==='HEAT_GENERATOR'" in src
