from ins_ei.config import SiteConfig
from ins_ei.runtime import Runtime


def test_runtime_collects_canonical_point():
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "test"},
        "plugin_instances": [{
            "id": "demo1",
            "plugin": "demo",
            "config": {"component_id": "boiler", "temperature_c": 70},
        }],
        "components": [{"id": "boiler", "kind": "HEAT_GENERATOR", "provider": "demo1"}],
    })

    runtime = Runtime(site)
    runtime.configure()
    runtime.start()
    runtime.collect_once()

    points = runtime.state.snapshot()
    assert len(points) == 1
    assert points[0].component_id == "boiler"
    assert points[0].point == "thermal.supply_temperature"
    assert points[0].value == 70.0
    assert runtime.health()["status"] == "OK"

    runtime.stop()
