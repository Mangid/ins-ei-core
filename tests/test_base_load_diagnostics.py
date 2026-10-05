from pathlib import Path
def test_base_load_diagnostics_visible():
    v=Path("src/ins_ei/forecast_validation.py").read_text()
    w=Path("src/ins_ei/webui.py").read_text()
    assert "def daily_base_diagnostics" in v
    assert "historical_daily_mean_kwh" in v
    assert "forecast_vs_history_ratio" in v
    assert "Basislast-Diagnose" in w
