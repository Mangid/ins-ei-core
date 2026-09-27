import pytest

from ins_ei.config import SiteConfig
from ins_ei.site_graph import SiteGraph


def make_site():
    return SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "home"},
        "plugin_instances": [
            {"id": "boiler_io", "plugin": "oekofen", "config": {}},
            {"id": "heater_io", "plugin": "mypv", "config": {}},
            {"id": "meter_io", "plugin": "shrdzm", "config": {}},
        ],
        "components": [
            {"id": "boiler", "kind": "HEAT_GENERATOR", "provider": "boiler_io"},
            {"id": "buffer", "kind": "BUFFER", "provider": "boiler_io"},
            {"id": "heater", "kind": "POWER_TO_HEAT", "provider": "heater_io"},
            {"id": "grid", "kind": "GRID", "provider": "meter_io"},
        ],
        "relations": [
            {"from": "boiler", "to": "buffer", "type": "HEATS"},
            {"from": "heater", "to": "buffer", "type": "HEATS"},
            {"from": "grid", "to": "heater", "type": "SUPPLIES"},
        ],
        "constraints": [
            {"id": "buffer_max", "type": "MAX_VALUE", "target": "buffer.thermal.temperature", "value": 75, "unit": "°C"},
        ],
    })


def test_graph_knows_physical_heat_paths():
    graph = SiteGraph(make_site())
    heat_sources = {c.id for c in graph.sources("buffer", "HEATS")}
    assert heat_sources == {"boiler", "heater"}
    assert [c.id for c in graph.targets("grid", "SUPPLIES")] == ["heater"]
    assert graph.constraints_for("buffer")[0].value == 75


def test_graph_rejects_unknown_component_in_relation():
    site = make_site()
    site.relations.append({"from": "ghost", "to": "buffer", "type": "HEATS"})
    with pytest.raises(ValueError, match="SITE_RELATION_SOURCE_UNKNOWN"):
        SiteGraph(site)


def test_graph_rejects_unknown_provider():
    site = make_site()
    site.components[0].provider = "missing_plugin_instance"
    with pytest.raises(ValueError, match="SITE_PROVIDER_UNKNOWN"):
        SiteGraph(site)
