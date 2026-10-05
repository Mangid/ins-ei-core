from pathlib import Path
def test_forecast_and_validation_share_balance_roles():
    f=Path("src/ins_ei/forecast_profiles.py").read_text()
    v=Path("src/ins_ei/forecast_validation.py").read_text()
    r=Path("src/ins_ei/runtime.py").read_text()
    for role in ("BALANCE_GRID","BALANCE_PV","BALANCE_BATTERY"):
        assert role in f and role in v
    assert "component_properties=self.component_properties" in r
    assert "AMBIGUOUS_BALANCE_SOURCE" in v
