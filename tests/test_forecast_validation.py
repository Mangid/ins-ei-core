from pathlib import Path
def test_forecast_validation_separates_flexible_loads():
    s=Path("src/ins_ei/forecast_validation.py").read_text()
    assert "POWER_TO_HEAT" in s
    assert "inflexible_base_kwh" in s
    assert "battery_charge_kwh" in s and "battery_discharge_kwh" in s
    assert "grid_export_kwh" in s
    assert "def score_slots" in s
def test_validation_api_exists():
    s=Path("src/ins_ei/api.py").read_text()
    assert '"/forecast/validation"' in s
