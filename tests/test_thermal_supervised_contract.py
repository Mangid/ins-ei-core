from pathlib import Path


def test_supervised_api_exposes_only_heat_once_for_oekofen():
    src = Path("src/ins_ei/api.py").read_text()
    assert '"/supervised/oekofen/heat-once"' in src
    assert '"/supervised/oekofen/pe-mode"' not in src


def test_runtime_tracks_external_control_state_changes():
    src = Path("src/ins_ei/runtime.py").read_text()
    assert '"operator.state_changed"' in src
    assert '"command.state_confirmed"' in src
    assert '"state.operating_mode"' in src
    assert '"state.one_time_charge"' in src


def test_thermal_shadow_does_not_execute_commands():
    src = Path("src/ins_ei/thermal_shadow.py").read_text()
    assert ".execute(" not in src
    assert '"DHW_HEAT_ONCE"' in src
    assert '"HEAT_GENERATOR_ENABLE"' in src
