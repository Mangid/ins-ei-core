from pathlib import Path
def test_forecast_alignment_is_bucketed_not_quadratic_and_uses_net_grid():
    s=Path("src/ins_ei/forecast_profiles.py").read_text()
    base=s[s.index("def base_load_profile_v4"):s.index("def pv_profile_v2")]
    assert "def bucket(rows)" in base
    assert "grid.export_power" in base
    assert "net_grid=grid_import.get(key,0.0)-grid_export.get(key,0.0)" in base
    assert "_nearest(" not in base
