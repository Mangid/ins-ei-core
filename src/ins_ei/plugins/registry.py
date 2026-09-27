from __future__ import annotations

from ins_ei.plugins.base import Plugin
from ins_ei.plugins.demo import DemoPlugin
from ins_ei.plugins.oekofen import OekofenPlugin
from ins_ei.plugins.mypv import MyPVPlugin

PLUGIN_REGISTRY: dict[str, type[Plugin]] = {
    "demo": DemoPlugin,
    "oekofen": OekofenPlugin,
    "mypv": MyPVPlugin,
}


def create_plugin(plugin_id: str, instance_id: str, config: dict) -> Plugin:
    try:
        cls = PLUGIN_REGISTRY[plugin_id]
    except KeyError as exc:
        raise ValueError(f"Plugin not installed: {plugin_id}") from exc
    return cls(instance_id, config)
