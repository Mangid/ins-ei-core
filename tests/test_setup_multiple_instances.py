def test_setup_renders_multiple_instances_of_same_plugin():
    from ins_ei.plugin_loader import PluginCatalog
    from ins_ei.setup_web import setup_html

    catalog = PluginCatalog("plugins")
    catalog.discover()
    site = {
        "plugin_instances": [
            {"id": "fronius_symo6", "plugin": "fronius", "config": {"host": "10.0.0.61", "component_prefix": "symo6"}},
            {"id": "fronius_symo5", "plugin": "fronius", "config": {"host": "10.0.0.62", "component_prefix": "symo5"}},
        ]
    }
    body = setup_html(catalog.installed().values(), existing_site=site).body.decode()
    assert "fronius_symo6" in body
    assert "fronius_symo5" in body
    assert "10.0.0.61" in body
    assert "10.0.0.62" in body
    assert "+ Instanz hinzufügen" in body
    assert "testPluginInstance" in body
