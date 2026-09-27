from __future__ import annotations

from datetime import datetime

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin


class DemoPlugin(Plugin):
    """Contract test plugin. Not a production device integration."""

    def __init__(self, instance_id: str, config: dict) -> None:
        super().__init__(instance_id, config)
        self.running = False

    def validate_config(self) -> None:
        if not self.config.get("component_id"):
            raise ValueError("demo plugin requires component_id")

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def health(self) -> PluginHealth:
        return PluginHealth(
            status=PluginStatus.RUNNING if self.running else PluginStatus.STOPPED,
            message="demo plugin running" if self.running else "demo plugin stopped",
        )

    def read_points(self) -> list[Point]:
        if not self.running:
            return []
        return [
            Point(
                component_id=self.config["component_id"],
                point="thermal.supply_temperature",
                value=float(self.config.get("temperature_c", 65.0)),
                unit="°C",
                quality=Quality.GOOD,
                observed_at=datetime.now().astimezone(),
                source=Source(plugin_instance=self.instance_id),
            )
        ]
