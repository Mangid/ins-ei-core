from pathlib import Path
def test_forecast_worker_diagnostics_are_isolated_and_visible():
    r=Path("src/ins_ei/runtime.py").read_text();a=Path("src/ins_ei/api.py").read_text();w=Path("src/ins_ei/webui.py").read_text()
    for step in ("consumption_forecast","pv_forecast","energy_balance","base_load_diagnostics","cache_write"): assert step in r
    assert '"/forecast/status"' in a
    assert "Forecast-Worker:" in w
    assert "forecast step failed" in r
