from pathlib import Path
def test_validation_is_background_cached_not_http_computed():
    a=Path("src/ins_ei/api.py").read_text()
    r=Path("src/ins_ei/runtime.py").read_text()
    h=Path("src/ins_ei/historian.py").read_text()
    endpoint=a[a.index('@app.get("/forecast/validation")'):a.index('@app.get("/metrics")')]
    assert "validate_energy_balance" not in endpoint
    assert "forecast_validation_cache" in endpoint
    assert "cache_put" in r and "daily_base_diagnostics" in r
    assert "CREATE TABLE IF NOT EXISTS runtime_cache" in h
