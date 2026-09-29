from pathlib import Path


def test_specialized_learning_namespaces_are_isolated():
    src = Path("src/ins_ei/learning_coordinator.py").read_text()
    assert 'model.metadata["electrical_fit"] = fit' in src
    assert 'model.metadata["battery_fit"] = fit' in src
    assert 'model.metadata["generic_fit"]' in src


def test_pv_orientation_uses_synchronized_power_buckets():
    src = Path("src/ins_ei/learning_coordinator.py").read_text()
    assert "replace(second=0, microsecond=0)" in src
    assert '"synchronized_samples"' in src
    assert '"maximum_w_per_kwp"' in src
