from __future__ import annotations

from datetime import datetime
from typing import Any

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin
from ins_ei.plugins.shrdzm_transport import ShrdzmTransport


class ShrdzmPlugin(Plugin):
    """SHRDZM grid meter plugin with canonical directional grid semantics."""

    def __init__(self, instance_id: str, config: dict[str, Any]) -> None:
        super().__init__(instance_id, config)
        self.transport: ShrdzmTransport | None = None
        self.running = False
        self.last_error: str | None = None
        self.last_diagnostics: dict[str, Any] = {}

    def validate_config(self) -> None:
        if not str(self.config.get("host", "")).strip():
            raise ValueError("shrdzm plugin requires host")

    def start(self) -> None:
        self.transport = ShrdzmTransport(
            host=self.config["host"],
            port=int(self.config.get("port", 502)),
            unit_id=int(self.config.get("unit_id", 1)),
            timeout=float(self.config.get("timeout", 5.0)),
        )
        self.running = True

    def stop(self) -> None:
        self.running = False

    def health(self) -> PluginHealth:
        if not self.running:
            return PluginHealth(status=PluginStatus.STOPPED, message="plugin stopped")
        if self.last_error:
            return PluginHealth(status=PluginStatus.DEGRADED, message=self.last_error)
        return PluginHealth(status=PluginStatus.RUNNING, message="SHRDZM connected")

    def read_points(self) -> list[Point]:
        if not self.running or self.transport is None:
            return []
        try:
            raw = self.transport.read_smartmeter()
            points = self._normalize(raw)
            self.last_diagnostics = {
                "signed_vendor_power_w": raw["signed_power_w"],
                "reactive_power_import_var": raw["reactive_power_import_var"],
                "reactive_power_export_var": raw["reactive_power_export_var"],
            }
            self.last_error = None
            return points
        except Exception as exc:
            self.last_error = str(exc)
            raise

    def _normalize(self, raw: dict[str, Any]) -> list[Point]:
        component = self.config.get("component_id", "grid")
        now = datetime.now().astimezone()
        source = Source(plugin_instance=self.instance_id)

        # Canonical INS-EI grid power is directional and always non-negative.
        # Vendor signed power remains diagnostics only.
        values = [
            ("grid.import_power", max(0.0, float(raw["power_import_w"])), "W"),
            ("grid.export_power", max(0.0, float(raw["power_export_w"])), "W"),
            ("energy.import_total", float(raw["import_energy_kwh"]), "kWh"),
            ("energy.export_total", float(raw["export_energy_kwh"]), "kWh"),
            ("electrical.voltage_l1", float(raw["voltage_l1_v"]), "V"),
            ("electrical.voltage_l2", float(raw["voltage_l2_v"]), "V"),
            ("electrical.voltage_l3", float(raw["voltage_l3_v"]), "V"),
            ("electrical.current_l1", float(raw["current_l1_a"]), "A"),
            ("electrical.current_l2", float(raw["current_l2_a"]), "A"),
            ("electrical.current_l3", float(raw["current_l3_a"]), "A"),
        ]
        return [
            Point(
                component_id=component, point=point, value=value, unit=unit,
                quality=Quality.GOOD, observed_at=now, source=source,
            )
            for point, value, unit in values
        ]

    def diagnostics(self) -> dict[str, Any]:
        return {"last_error": self.last_error, **self.last_diagnostics}
