from pathlib import Path
def test_forecast_accuracy_v1_contracts():
    h=Path("src/ins_ei/historian.py").read_text();r=Path("src/ins_ei/runtime.py").read_text();a=Path("src/ins_ei/api.py").read_text();w=Path("src/ins_ei/webui.py").read_text()
    assert "forecast_snapshots" in h and "record_forecast_slots" in h
    assert "snapshot_consumption" in r and "snapshot_pv" in r and "forecast_accuracy" in r
    assert '"/forecast/accuracy"' in a
    assert "Forecast-Genauigkeit" in w and "MAE" in w and "Bias" in w
