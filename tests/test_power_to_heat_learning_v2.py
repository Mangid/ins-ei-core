from pathlib import Path

def test_power_to_heat_v2_is_contextualized():
    src=Path("src/ins_ei/learning_coordinator.py").read_text()
    assert '"0_3KW"' in src
    assert '"3_6KW"' in src
    assert '"6_9KW"' in src
    assert '"45_55C"' in src
    assert '"55_65C"' in src
    assert 'model.metadata["power_to_heat_v2_fit"] = p2h_v2' in src
    assert 'p2h <= 100.0' in src
