from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import SiteConfig
from .models import PluginHealth, PluginStatus
from .plugins.base import Plugin
from .plugins.registry import create_plugin
from .state import StateStore

log = logging.getLogger("ins_ei.runtime")


@dataclass
class ManagedPlugin:
    plugin: Plugin
    status: PluginStatus = PluginStatus.CONFIGURED
    error: str | None = None


class Runtime:
    def __init__(self, site: SiteConfig) -> None:
        self.site = site
        self.state = StateStore()
        self.plugins: dict[str, ManagedPlugin] = {}

    def configure(self) -> None:
        for cfg in self.site.plugin_instances:
            plugin = create_plugin(cfg.plugin, cfg.id, cfg.config)
            plugin.validate_config()
            self.plugins[cfg.id] = ManagedPlugin(plugin=plugin)
            log.info("plugin configured | instance=%s plugin=%s", cfg.id, cfg.plugin)

    def start(self) -> None:
        for instance_id, managed in self.plugins.items():
            managed.status = PluginStatus.STARTING
            try:
                managed.plugin.start()
                managed.status = PluginStatus.RUNNING
                log.info("plugin started | instance=%s", instance_id)
            except Exception as exc:
                managed.status = PluginStatus.FAILED
                managed.error = str(exc)
                log.exception("plugin start failed | instance=%s", instance_id)

    def collect_once(self) -> None:
        for instance_id, managed in self.plugins.items():
            if managed.status not in {PluginStatus.RUNNING, PluginStatus.DEGRADED}:
                continue
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

    def health(self) -> dict:
        statuses = {
            key: {"status": value.status, "error": value.error}
            for key, value in self.plugins.items()
        }
        failed = any(v.status == PluginStatus.FAILED for v in self.plugins.values())
        degraded = any(v.status == PluginStatus.DEGRADED for v in self.plugins.values())
        overall = "FAILED" if failed else "DEGRADED" if degraded else "OK"
        return {"status": overall, "site": self.site.site.id, "plugins": statuses}
