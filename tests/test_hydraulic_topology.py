import pytest

from ins_ei.config import SiteConfig
from ins_ei.site_graph import SiteGraph


def test_port_level_hydraulics_and_sensor_positions():
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "hydraulic"},
        "components": [
            {
                "id": "boiler", "kind": "HEAT_GENERATOR",
                "ports": [
                    {"id": "supply", "type": "HYDRAULIC_SUPPLY"},
                    {"id": "return", "type": "HYDRAULIC_RETURN"},
                ],
            },
            {
                "id": "buffer", "kind": "BUFFER",
                "ports": [
                    {"id": "top", "type": "HYDRAULIC"},
                    {"id": "bottom", "type": "HYDRAULIC"},
                ],
                "sensors": [
                    {"id": "top_sensor", "point": "thermal.temperature_upper", "position": 0.1}
                ],
            },
        ],
        "connections": [
            {"from": "boiler.supply", "to": "buffer.top", "medium": "WATER"},
            {"from": "buffer.bottom", "to": "boiler.return", "medium": "WATER"},
        ],
    })
    graph = SiteGraph(site)
    assert len(graph.connections) == 2
    assert graph.components["buffer"].sensors[0].position == 0.1


def test_unknown_port_is_rejected():
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "bad"},
        "components": [
            {"id": "a", "kind": "BUFFER", "ports": [{"id": "top", "type": "HYDRAULIC"}]},
            {"id": "b", "kind": "BUFFER", "ports": [{"id": "bottom", "type": "HYDRAULIC"}]},
        ],
        "connections": [{"from": "a.missing", "to": "b.bottom"}],
    })
    with pytest.raises(ValueError, match="SITE_CONNECTION_SOURCE_UNKNOWN"):
        SiteGraph(site)


def test_sensor_position_must_be_normalized():
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "bad-sensor"},
        "components": [{
            "id": "buffer", "kind": "BUFFER",
            "sensors": [{"id": "x", "position": 1.5}],
        }],
    })
    with pytest.raises(ValueError, match="SITE_SENSOR_POSITION_RANGE"):
        SiteGraph(site)
