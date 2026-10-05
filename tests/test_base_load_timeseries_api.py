from pathlib import Path
def test_base_load_diagnostics_uses_timeseries_series_api():
    r=Path("src/ins_ei/runtime.py").read_text()
    assert 'self.timeseries.series("forecast.consumption_energy")' in r
    assert 'self.timeseries.get("forecast.consumption_energy")' not in r
