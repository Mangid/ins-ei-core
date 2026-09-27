from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from .config import SiteConfig
from .models import PluginHealth, PluginStatus
from .plugins.base import Plugin
from .plugin_loader import PluginCatalog
from .state import StateStore
from .site_graph import SiteGraph
from .strategy import StrategyContext
from .strategy_loader import build_strategy_engine
from .safety import SafetyController
from .audit import AuditLog
from .metrics import Metrics
from .timeseries import TimeSeriesStore
from .historian import Historian

log = logging.getLogger("ins_ei.runtime")


@dataclass
class ManagedPlugin:
    plugin: Plugin
    status: PluginStatus = PluginStatus.CONFIGURED
    error: str | None = None
    last_successful_read_at: datetime | None = None
    last_read_attempt_at: datetime | None = None


class Runtime:
    def __init__(
        self,
        site: SiteConfig,
        plugin_dir: str = "plugins",
        historian_path: str | None = None,
    ) -> None:
        self.site = site
        self.state = StateStore()
        self.graph = SiteGraph(site)
        self.strategy_engine = build_strategy_engine(site, self.graph)
        self.last_decision = None
        self.safety = SafetyController()
        self.metrics = Metrics()
        self.timeseries = TimeSeriesStore()
        self.historian = Historian(
            historian_path or f"data/{site.site.id}/historian.sqlite3"
        )
        self.context_version = "site-v1"
        self.last_correlation_id = None
        self.audit = AuditLog(site.site.id)
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
            self.metrics.inc("plugin_configured_total")
            self.audit.record("plugin.configured", instance=cfg.id, plugin=cfg.plugin, version=manifest.version)

    def start_instance(self, instance_id: str) -> None:
        managed = self.plugins[instance_id]
        managed.status = PluginStatus.STARTING
        try:
            managed.plugin.start()
            managed.status = PluginStatus.RUNNING
            managed.error = None
            log.info("plugin started | instance=%s", instance_id)
            self.metrics.inc("plugin_start_success_total")
            self.audit.record("plugin.started", instance=instance_id)
        except Exception as exc:
            managed.status = PluginStatus.FAILED
            managed.error = str(exc)
            log.exception("plugin start failed | instance=%s", instance_id)
            self.metrics.inc("plugin_start_failed_total")
            self.audit.record("plugin.start_failed", instance=instance_id, error=str(exc))

    def start(self) -> None:
        for instance_id in self.plugins:
            self.start_instance(instance_id)

    def collect_instance(self, instance_id: str) -> None:
        managed = self.plugins[instance_id]
        if managed.status not in {PluginStatus.RUNNING, PluginStatus.DEGRADED}:
            return
        managed.last_read_attempt_at = datetime.now().astimezone()
        try:
            points = managed.plugin.read_points()
            self.state.ingest(points)
            self.historian.record_points(self.site.site.id, points, self.context_version)
            managed.last_successful_read_at = datetime.now().astimezone()
            health = managed.plugin.health()
            managed.status = health.status
            managed.error = None if health.status == PluginStatus.RUNNING else health.message
            log.info("plugin collected | instance=%s points=%d status=%s", instance_id, len(points), managed.status)
            self.metrics.inc("collect_success_total")
            self.metrics.inc("points_ingested_total", len(points))
            self.metrics.set(f"plugin.{instance_id}.last_read_ok", 1)
            self.metrics.set(f"plugin.{instance_id}.points_last_read", len(points))
        except Exception as exc:
            managed.status = PluginStatus.DEGRADED
            managed.error = str(exc)
            log.exception("plugin collect failed | instance=%s", instance_id)
            self.metrics.inc("collect_failed_total")
            self.metrics.set(f"plugin.{instance_id}.last_read_ok", 0)
            self.audit.record("plugin.collect_failed", instance=instance_id, error=str(exc))

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
        self.metrics.inc("strategy_evaluation_total")
        if self.safety.state().emergency_stop:
            self.metrics.inc("strategy_blocked_emergency_stop_total")
        self.last_decision = self.strategy_engine.evaluate(
            StrategyContext(self.graph, self.state, self.timeseries)
        )
        self.last_correlation_id = self.historian.new_correlation_id()
        self.historian.record_decision(
            self.site.site.id,
            self.last_decision,
            self.last_correlation_id,
            self.context_version,
        )
        self.audit.record(
            "strategy.decision",
            action=self.last_decision.action,
            strategy=self.last_decision.winning_strategy,
            priority=self.last_decision.priority.name,
            reason=self.last_decision.reason,
            intents=[
                {"target": i.target, "command": i.command, "parameters": i.parameters}
                for i in self.last_decision.intents
            ],
        )
        return self.last_decision

    def health(self) -> dict:
        now = datetime.now().astimezone()
        statuses = {}
        for key, value in self.plugins.items():
            read_age = (
                max(0.0, (now - value.last_successful_read_at).total_seconds())
                if value.last_successful_read_at else None
            )
            statuses[key] = {
                "status": value.status,
                "error": value.error,
                "last_successful_read_at": (
                    value.last_successful_read_at.isoformat()
                    if value.last_successful_read_at else None
                ),
                "last_read_age_seconds": read_age,
            }
            if read_age is not None:
                self.metrics.set(f"plugin.{key}.last_read_age_seconds", read_age)
        failed = any(v.status == PluginStatus.FAILED for v in self.plugins.values())
        degraded = any(v.status == PluginStatus.DEGRADED for v in self.plugins.values())
        overall = "FAILED" if failed else "DEGRADED" if degraded else "OK"
        return {"status": overall, "site": self.site.site.id, "plugins": statuses}
