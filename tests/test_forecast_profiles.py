from pathlib import Path
def test_legacy_forecasts_are_ported_to_local_core():
    s=Path("src/ins_ei/forecast_profiles.py").read_text()
    assert "INS_EI_BASE_LOAD_PROFILE_V4" in s
    assert "INS_EI_PV_PROFILE_V2" in s
    assert "forecast.consumption_energy" in s
    assert "forecast.pv_energy" in s
    assert "power.electrical" in s
    assert "NEIGHBOUR_FALLBACK" in s
