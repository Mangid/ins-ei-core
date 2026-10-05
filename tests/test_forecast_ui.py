from pathlib import Path
def test_forecast_page_surfaces_24h_energy_series():
    s=Path("src/ins_ei/webui.py").read_text()
    assert 'data-page="forecast"' in s
    assert 'id="fcLoadTotal"' in s and 'id="fcPvTotal"' in s
    assert "forecast.consumption_energy" in s and "forecast.pv_energy" in s
    assert "j('/timeseries')" in s
