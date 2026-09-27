from pathlib import Path

import pytest

from ins_ei.plugin_loader import PluginCatalog
from ins_ei.plugins.demo import DemoPlugin


def test_catalog_discovers_manifests():
    catalog = PluginCatalog(Path("plugins"))
    installed = catalog.discover()
    assert {"demo", "oekofen", "mypv", "shrdzm"} <= set(installed)


def test_catalog_loads_entrypoint_without_static_registry():
    catalog = PluginCatalog(Path("plugins"))
    catalog.discover()
    plugin = catalog.create("demo", "demo1", {"component_id": "x"})
    assert isinstance(plugin, DemoPlugin)


def test_unknown_plugin_fails_cleanly():
    catalog = PluginCatalog(Path("plugins"))
    catalog.discover()
    with pytest.raises(ValueError, match="Plugin not installed"):
        catalog.create("does-not-exist", "x", {})
