from pathlib import Path
def test_startup_collect_once_does_not_fit_models_or_forecasts():
    r=Path("src/ins_ei/runtime.py").read_text()
    body=r[r.index("    def collect_once"):r.index("    def reload_plugin_type")]
    assert "fit_buffer_state_v2" not in body
    assert "base_load_profile_v4" not in body
    assert "pv_profile_v2" not in body
    assert "def update_forecasts" in r
def test_background_loop_refreshes_buffer_and_forecasts():
    m=Path("src/ins_ei/main.py").read_text()
    assert "runtime.learning.fit_buffer_state_v2()" in m
    assert "runtime.update_forecasts()" in m
