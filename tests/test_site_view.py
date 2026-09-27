from datetime import datetime

from ins_ei.config import SiteConfig
from ins_ei.models import Point, Quality, Source
from ins_ei.site_graph import SiteGraph
from ins_ei.site_view import build_site_view
from ins_ei.state import StateStore


def test_site_view_combines_topology_and_live_sensor_value():
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "visual"},
        "components": [{
            "id": "buffer",
            "kind": "BUFFER",
            "ports": [
                {"id": "top", "type": "HYDRAULIC"},
                {"id": "bottom", "type": "HYDRAULIC"},
            ],
            "sensors": [{
                "id": "top_sensor",
                "point": "thermal.temperature_upper",
                "position": 0.1,
            }],
        }],
    })
    state = StateStore()
    state.ingest([Point(
        component_id="buffer",
        point="thermal.temperature_upper",
        value=62.5,
        unit="°C",
        quality=Quality.GOOD,
        observed_at=datetime.now().astimezone(),
        source=Source(plugin_instance="test"),
    )])

    view = build_site_view(SiteGraph(site), state)
    buffer = view["components"][0]
    assert buffer["kind"] == "BUFFER"
    assert buffer["sensors"][0]["value"]["value"] == 62.5
    assert buffer["sensors"][0]["position"] == 0.1
