from __future__ import annotations

from datetime import datetime
from typing import Any

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin


class EnergyReferencePlugin(Plugin):
    """Reference contract plugin for PV/BATTERY semantics.

    It is not a production hardware integration. It proves the canonical
    interface before Victron/Huawei/Fronius-specific transports are added.
    """

    def __init__(self, instance_id: str, config: dict[str, Any]) -> None:
        super().__init__(instance_id, config)
        self.running = False

    def validate_config(self) -> None:
        if not self.config.get("battery_component"):
            raise ValueError("energy_reference requires battery_component")
        if not self.config.get("pv_component"):
            raise ValueError("energy_reference requires pv_component")

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def health(self) -> PluginHealth:
        return PluginHealth(
            status=PluginStatus.RUNNING if self.running else PluginStatus.STOPPED,
            message="reference energy plugin",
        )

    def read_points(self) -> list[Point]:
        if not self.running:
            return []
        now = datetime.now().astimezone()
        source = Source(plugin_instance=self.instance_id)
        battery = self.config["battery_component"]
        pv = self.config["pv_component"]
        values = self.config.get("values", {})
        specs = [
            (pv, "pv.generation_power", "W", values.get("pv_generation_w", 0)),
            (battery, "battery.soc", "%", values.get("soc_percent", 50)),
            (battery, "battery.charge_power", "W", values.get("charge_power_w", 0)),
            (battery, "battery.discharge_power", "W", values.get("discharge_power_w", 0)),
            (battery, "battery.max_charge_power", "W", values.get("max_charge_power_w", 5000)),
            (battery, "battery.max_discharge_power", "W", values.get("max_discharge_power_w", 5000)),
            (battery, "battery.capacity_usable", "kWh", values.get("capacity_usable_kwh", 10)),
        ]
        return [
            Point(
                component_id=component,
                point=point,
                value=float(value),
                unit=unit,
                quality=Quality.GOOD,
                observed_at=now,
                source=source,
            )
            for component, point, unit, value in specs
        ]
