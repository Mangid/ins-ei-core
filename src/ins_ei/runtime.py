from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import SiteConfig
from .models import PluginHealth, PluginStatus
from .plugins.base import Plugin
from .plugin_loader import PluginCatalog
from .state import StateStore
from .site_graph import SiteGraph
from .strategy import StrategyContext
from .strategy_loader import build_strategy_engine

log = logging.getLogger("ins_ei.runtime")


@dataclass
class ManagedPlugin:
    plugin: Plugin
    status: PluginStatus = PluginStatus.CONFIGURED
    error: str | None = None


class Runtime:
    def __init__(self, site: SiteConfig, plugin_dir: str = "plugins") -> None:
        self.site = site
        self.state = StateStore()
        self.graph = SiteGraph(site)
        self.strategy_engine = build_strategy_engine(site, self.graph)
        self.last_decision = None
        self.catalog = PluginCatalog(plugin_dir)
        self.catalog.discover()
        self.plugins: dict[str, ManagedPlugin] = {}
        self.instance_configs = {cfg.id: cfg for cfg in site.plugin_instances}
        self.instance_plugin_ids = {cfg.id: cfg.plugin for cfg in site.plugin_instances}

    def configure(self) -> None:
        for cfg in self.site.plugin_instances:
            manifest = self.catalog.manifest(cfg.plugin)
            plugin = self.catalog.create(cfg.plugin, cfg.id, cfg.config)
            plugin.validate_config()
            self.plugins[cfg.id] = ManagedPlugin(plugin=plugin)
            log.info(
                "plugin configured | instance=%s plugin=%s version=%s capabilities=%s",
                cfg.id, cfg.plugin, manifest.version, ",".join(manifest.capabilities),
            )

    def start_instance(self, instance_id: str) -> None:
        managed = self.plugins[instance_id]
        managed.status = PluginStatus.STARTING
        try:
            managed.plugin.start()
            managed.status = PluginStatus.RUNNING
            managed.error = None
            log.info("plugin started | instance=%s", instance_id)
        except Exception as exc:
            managed.status = PluginStatus.FAILED
            managed.error = str(exc)
            log.exception("plugin start failed | instance=%s", instance_id)

    def start(self) -> None:
        for instance_id in self.plugins:
            self.start_instance(instance_id)

    def collect_instance(self, instance_id: str) -> None:
        managed = self.plugins[instance_id]
        if managed.status not in {PluginStatus.RUNNING, PluginStatus.DEGRADED}:
            return
        try:
            points = managed.plugin.read_points()
            self.state.ingest(points)
            health = managed.plugin.health()
            managed.status = health.status
            managed.error = None if health.status == PluginStatus.RUNNING else health.message
            log.info("plugin collected | instance=%s points=%d status=%s", instance_id, len(points), managed.status)
        except Exception as exc:
            managed.status = PluginStatus.DEGRADED
            managed.error = str(exc)
            log.exception("plugin collect failed | instance=%s", instance_id)

    def collect_once(self) -> None:
        for instance_id in self.plugins:
            self.collect_instance(instance_id)

    def reload_plugin_type(self, plugin_id: str) -> None:
        self.catalog.discover()
        for instance_id, configured_plugin_id in self.instance_plugin_ids.items():
            if configured_plugin_id != plugin_id:
                continue
            cfg = self.instance_configs[instance_id]
            plugin = self.catalog.create(cfg.plugin, cfg.id, cfg.config)
            plugin.validate_config()
            self.plugins[instance_id] = ManagedPlugin(plugin=plugin)

    def stop(self) -> None:
        for instance_id, managed in self.plugins.items():
            managed.status = PluginStatus.STOPPING
            try:
                managed.plugin.stop()
                managed.status = PluginStatus.STOPPED
            except Exception as exc:
                managed.status = PluginStatus.FAILED
                managed.error = str(exc)
                log.exception("plugin stop failed | instance=%s", instance_id)

    def evaluate_strategy(self):
        self.last_decision = self.strategy_engine.evaluate(
            StrategyContext(self.graph, self.state)
        )
        return self.last_decision

    def health(self) -> dict:
        statuses = {
            key: {"status": value.status, "error": value.error}
            for key, value in self.plugins.items()
        }
        failed = any(v.status == PluginStatus.FAILED for v in self.plugins.values())
        degraded = any(v.status == PluginStatus.DEGRADED for v in self.plugins.values())
        overall = "FAILED" if failed else "DEGRADED" if degraded else "OK"
        return {"status": overall, "site": self.site.site.id, "plugins": statuses}
