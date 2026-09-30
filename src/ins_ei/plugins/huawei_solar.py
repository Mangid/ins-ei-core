from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin
from ins_ei.plugins.huawei_modbus_transport import HuaweiModbusTransport

log = logging.getLogger("ins_ei.plugin.huawei_solar")


class HuaweiSolarPlugin(Plugin):
    """Generic read-only Huawei SUN2000/LUNA/Smart Meter Modbus provider."""

    def __init__(self, instance_id: str, config: dict[str, Any]) -> None:
        super().__init__(instance_id, config)
        self.transport: HuaweiModbusTransport | None = None
        self.running = False
        self.last_error: str | None = None
        self.last_diagnostics: dict[str, Any] = {}

    def validate_config(self) -> None:
        if not str(self.config.get("host", "")).strip():
            raise ValueError("huawei_solar requires host")

    def start(self) -> None:
        self.transport = HuaweiModbusTransport(
            self.config["host"], int(self.config.get("port", 502)),
            float(self.config.get("timeout", 5.0)),
        )
        self.running = True

    def stop(self) -> None:
        self.running = False

    def health(self) -> PluginHealth:
        if not self.running:
            return PluginHealth(status=PluginStatus.STOPPED, message="plugin stopped")
        if self.last_error:
            return PluginHealth(status=PluginStatus.DEGRADED, message=self.last_error)
        if not self.last_diagnostics:
            return PluginHealth(status=PluginStatus.STARTING, message="waiting for Huawei Modbus telemetry")
        return PluginHealth(status=PluginStatus.RUNNING, message="Huawei Modbus telemetry active")

    def _point(self, component: str, name: str, value: float, unit: str, now, source) -> Point:
        return Point(component_id=component, point=name, value=value, unit=unit,
                     quality=Quality.GOOD, observed_at=now, source=source)

    def _unit_ids(self) -> list[int]:
        raw = self.config.get("inverter_unit_ids", "1")
        if isinstance(raw, str):
            raw = [x.strip() for x in raw.split(",") if x.strip()]
        return [int(x) for x in raw]

    def read_points(self) -> list[Point]:
        if not self.running or self.transport is None:
            return []
        try:
            now = datetime.now().astimezone()
            source = Source(plugin_instance=self.instance_id)
            points: list[Point] = []
            units = self._unit_ids()
            models: dict[int, str] = {}
            total_pv = 0.0

            # Huawei common inverter registers. Model name at 30000; DC input
            # power at 32064 and AC active power at 32080 are intentionally kept
            # separate. Multiple inverter unit IDs are aggregated into logical PV.
            for index, unit in enumerate(units, start=1):
                model = self.transport.string(unit, 30000, 15)
                models[unit] = model
                input_power = float(self.transport.i32(self.transport.read_registers(unit, 32064, 2)))
                active_power = float(self.transport.i32(self.transport.read_registers(unit, 32080, 2)))
                total_pv += max(0.0, input_power)
                component = f"huawei_inverter_{index}"
                points += [
                    self._point(component, "pv.generation_power", max(0.0, input_power), "W", now, source),
                    self._point(component, "power.output", active_power, "W", now, source),
                ]

            points.append(self._point("pv", "pv.generation_power", total_pv, "W", now, source))

            # Plant-level meter and storage are read from the primary inverter.
            primary = int(self.config.get("primary_unit_id", units[0]))
            meter_power = float(self.transport.i32(self.transport.read_registers(primary, 37113, 2)))
            points += [
                self._point("grid_huawei", "grid.export_power", max(0.0, meter_power), "W", now, source),
                self._point("grid_huawei", "grid.import_power", max(0.0, -meter_power), "W", now, source),
            ]

            # Modern aggregate LUNA registers (documented for current SUN2000
            # families). Fall back to legacy unit-1 registers when unavailable.
            battery_profile = "aggregate_377xx"
            try:
                rated_wh = float(self.transport.u32(self.transport.read_registers(primary, 37758, 2)))
                soc = self.transport.read_registers(primary, 37760, 1)[0] / 10.0
                battery_power = float(self.transport.i32(self.transport.read_registers(primary, 37765, 2)))
            except Exception:
                battery_profile = "legacy_370xx"
                rated_wh = 0.0
                soc = self.transport.read_registers(primary, 37004, 1)[0] / 10.0
                battery_power = float(self.transport.i32(self.transport.read_registers(primary, 37001, 2)))

            points += [
                self._point("battery", "battery.soc", soc, "%", now, source),
                self._point("battery", "battery.charge_power", max(0.0, battery_power), "W", now, source),
                self._point("battery", "battery.discharge_power", max(0.0, -battery_power), "W", now, source),
            ]
            if rated_wh > 0:
                points.append(self._point("battery", "battery.capacity", rated_wh / 1000.0, "kWh", now, source))

            self.last_diagnostics = {
                "transport": "modbus_tcp",
                "host": self.config["host"],
                "port": int(self.config.get("port", 502)),
                "inverter_unit_ids": units,
                "models": models,
                "battery_profile": battery_profile,
                "points": len(points),
            }
            self.last_error = None
            return points
        except Exception as exc:
            self.last_error = str(exc)
            log.warning("Huawei Modbus read failed | instance=%s error=%s", self.instance_id, exc)
            raise

    def discover_components(self, points: list[Point]) -> list[dict[str, Any]]:
        present = {p.component_id for p in points}
        result = []
        for component_id, kind in [
            ("pv", "PV"), ("battery", "BATTERY"), ("grid_huawei", "GRID_METER")
        ]:
            if component_id in present:
                result.append({"id": component_id, "kind": kind, "ready": True})
        for component_id in sorted(x for x in present if x.startswith("huawei_inverter_")):
            result.append({"id": component_id, "kind": "PV_INVERTER", "ready": True})
        return result

    def diagnostics(self) -> dict[str, Any]:
        return {"last_error": self.last_error, **self.last_diagnostics}

    def execute(self, command: str, parameters: dict[str, Any] | None = None):
        raise NotImplementedError("Huawei Solar V1 plugin is read-only")
