from pathlib import Path

def test_buffer_state_v21_uses_scalar_state_history_and_aggregates_drivers():
    h=Path("src/ins_ei/historian.py").read_text()
    l=Path("src/ins_ei/learning_coordinator.py").read_text()
    assert "def series(" in h
    assert 'text_series(cid, p)' in l
    assert 'operating = nearest' in l
    assert '"driver_values"' in l
    assert '"mean":sum(values)/len(values)' in l
    assert 'model.metadata["phase"] = "BUFFER_STATE_V2_1"' in l
