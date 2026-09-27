import pytest

from ins_ei.config import SiteConfig
from ins_ei.site_graph import SiteGraph
from ins_ei.strategy_loader import build_strategy_engine


def site_with_strategy(minimum=50, source="boiler"):
    return SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "any-site"},
        "plugin_instances": [{"id": "io", "plugin": "oekofen", "config": {}}],
        "components": [
            {"id": "boiler", "kind": "HEAT_GENERATOR", "provider": "io"},
            {"id": "dhw", "kind": "DHW", "provider": "io"},
        ],
        "relations": [{"from": "boiler", "to": "dhw", "type": "HEATS"}],
        "strategy": {
            "modules": [{
                "id": "dhw_minimum",
                "enabled": True,
                "config": {
                    "dhw_component": "dhw",
                    "minimum_c": minimum,
                    "heat_source": source,
                },
            }]
        },
    })


def test_strategy_is_built_from_site_config():
    site = site_with_strategy(48)
    engine = build_strategy_engine(site, SiteGraph(site))
    assert len(engine.modules) == 1
    assert engine.modules[0].minimum_c == 48


def test_strategy_rejects_unconnected_heat_source():
    site = site_with_strategy()
    site.components.append({"id": "other", "kind": "HEAT_GENERATOR", "provider": "io"})
    site.strategy["modules"][0]["config"]["heat_source"] = "other"
    with pytest.raises(ValueError, match="STRATEGY_HEAT_SOURCE_NOT_CONNECTED"):
        build_strategy_engine(site, SiteGraph(site))


def test_disabled_strategy_is_not_loaded():
    site = site_with_strategy()
    site.strategy["modules"][0]["enabled"] = False
    engine = build_strategy_engine(site, SiteGraph(site))
    assert engine.modules == []
