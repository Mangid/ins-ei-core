from ins_ei.main import build_runtime


def test_demo_runtime_builds_with_explicit_paths(tmp_path):
    runtime = build_runtime(
        "config/site.example.yaml",
        plugin_dir="plugins",
        data_dir=str(tmp_path),
    )
    try:
        assert runtime.health()["site"] == "demo-site"
        assert runtime.state.snapshot()
    finally:
        runtime.stop()
