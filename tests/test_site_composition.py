from ins_ei.config import SiteConfig


def test_residential_site_composes_multiple_vendor_plugins():
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "mixed-site"},
        "plugin_instances": [
            {"id": "boiler_io", "plugin": "oekofen", "config": {"host": "boiler", "password": "x"}},
            {"id": "heater_io", "plugin": "mypv", "config": {"host": "heater"}},
            {"id": "grid_io", "plugin": "shrdzm", "config": {"host": "meter"}},
        ],
        "components": [
            {"id": "boiler", "kind": "HEAT_GENERATOR", "provider": "boiler_io"},
            {"id": "heater", "kind": "POWER_TO_HEAT", "provider": "heater_io"},
            {"id": "grid", "kind": "GRID", "provider": "grid_io"},
        ],
        "relations": [
            {"from": "grid", "to": "heater", "type": "SUPPLIES"},
        ],
    })
    assert {p.plugin for p in site.plugin_instances} == {"oekofen", "mypv", "shrdzm"}
    assert {c.kind for c in site.components} == {"HEAT_GENERATOR", "POWER_TO_HEAT", "GRID"}
