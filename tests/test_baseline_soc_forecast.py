from pathlib import Path
def test_baseline_soc_forecast_contract():
    s=Path("src/ins_ei/soc_forecast.py").read_text();r=Path("src/ins_ei/runtime.py").read_text();w=Path("src/ins_ei/webui.py").read_text()
    assert "forecast.battery_soc" in s
    assert "battery.soc" in s and "capacity_kwh" in s and "min_soc_pct" in s
    assert 'run("soc_forecast"' in r
    assert "SOC Baseline" in w and "ySoc" in w
