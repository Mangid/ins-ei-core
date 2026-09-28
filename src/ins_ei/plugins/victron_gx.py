from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin
from ins_ei.plugins.victron_modbus_transport import VictronModbusTransport

log = logging.getLogger("ins_ei.plugin.victron_gx")


class VictronGXPlugin(Plugin):
    """Read-only Victron GX Modbus TCP provider."""

    def __init__(self, instance_id: str, config: dict[str, Any]) -> None:
        super().__init__(instance_id, config)
        self.transport: VictronModbusTransport | None = None
        self.running = False
        self.last_error: str | None = None
        self.last_diagnostics: dict[str, Any] = {}

    def validate_config(self) -> None:
        if not str(self.config.get("host", "")).strip():
            raise ValueError("victron_gx requires host")

    def start(self) -> None:
        self.transport = VictronModbusTransport(
            self.config["host"], int(self.config.get("port", 502)),
            float(self.config.get("timeout", 5.0)),
        )
        self.running = True
        log.info("modbus configured | instance=%s host=%s port=%s",
                 self.instance_id, self.config["host"], self.config.get("port", 502))

    def stop(self) -> None:
        self.running = False

    def health(self) -> PluginHealth:
        if not self.running:
            return PluginHealth(status=PluginStatus.STOPPED, message="plugin stopped")
        if self.last_error:
            return PluginHealth(status=PluginStatus.DEGRADED, message=self.last_error)
        if not self.last_diagnostics:
            return PluginHealth(status=PluginStatus.STARTING, message="waiting for Modbus telemetry")
        return PluginHealth(status=PluginStatus.RUNNING, message="Victron GX Modbus telemetry active")

    def _point(self, component: str, name: str, value: float, unit: str, now, source) -> Point:
        return Point(component_id=component, point=name, value=value, unit=unit,
                     quality=Quality.GOOD, observed_at=now, source=source)

    def read_points(self) -> list[Point]:
        if not self.running or self.transport is None:
            return []
        try:
            now = datetime.now().astimezone()
            source = Source(plugin_instance=self.instance_id)
            points: list[Point] = []

            battery_unit = int(self.config.get("battery_unit_id", 225))
            grid_unit = int(self.config.get("grid_unit_id", 30))
            raw_pv_units = self.config.get("pv_unit_ids", [22, 23])
            if isinstance(raw_pv_units, str):
                raw_pv_units = [x.strip() for x in raw_pv_units.split(",") if x.strip()]
            pv_units = [int(x) for x in raw_pv_units]

            # com.victronenergy.battery:
            # 259 voltage /100 V, 261 signed current /10 A, 262 temp /10 C,
            # 266 SOC /10 %. Power is derived from V*I.
            b = self.transport.read_registers(battery_unit, 259, 8)
            voltage = b[0] / 100.0
            current = self.transport.signed16(b[2]) / 10.0
            temperature = self.transport.signed16(b[3]) / 10.0
            soc = b[7] / 10.0
            power = voltage * current
            points += [
                self._point("battery", "battery.soc", soc, "%", now, source),
                self._point("battery", "electrical.voltage_dc", voltage, "V", now, source),
                self._point("battery", "electrical.current_dc", current, "A", now, source),
                self._point("battery", "thermal.temperature", temperature, "°C", now, source),
                self._point("battery", "battery.charge_power", max(0.0, power), "W", now, source),
                self._point("battery", "battery.discharge_power", max(0.0, -power), "W", now, source),
            ]

            # com.victronenergy.grid: phase powers 2600..2602, signed:
            # positive import, negative export.
            g = self.transport.read_registers(grid_unit, 2600, 3)
            phase_power = [float(self.transport.signed16(x)) for x in g]
            total_grid = sum(phase_power)
            points += [
                self._point("grid_victron", f"power.output_l{i+1}", phase_power[i], "W", now, source)
                for i in range(3)
            ]
            points += [
                self._point("grid_victron", "grid.import_power", max(0.0, total_grid), "W", now, source),
                self._point("grid_victron", "grid.export_power", max(0.0, -total_grid), "W", now, source),
            ]

            # com.victronenergy.pvinverter: per-phase power registers.
            total_pv = 0.0
            for index, unit in enumerate(pv_units, start=1):
                p1 = self.transport.read_registers(unit, 1029, 1)[0]
                p2 = self.transport.read_registers(unit, 1033, 1)[0]
                p3 = self.transport.read_registers(unit, 1037, 1)[0]
                pv_power = float(p1 + p2 + p3)
                total_pv += pv_power
                component = f"pv_inverter_{index}"
                points += [
                    self._point(component, "pv.generation_power", pv_power, "W", now, source),
                    self._point(component, "power.output_l1", float(p1), "W", now, source),
                    self._point(component, "power.output_l2", float(p2), "W", now, source),
                    self._point(component, "power.output_l3", float(p3), "W", now, source),
                ]
            points.append(self._point("pv", "pv.generation_power", total_pv, "W", now, source))

            self.last_diagnostics = {
                "transport": "modbus_tcp",
                "battery_unit_id": battery_unit,
                "grid_unit_id": grid_unit,
                "pv_unit_ids": pv_units,
                "points": len(points),
            }
            self.last_error = None
            log.info(
                "modbus telemetry | instance=%s points=%d battery_soc=%.1f pv_w=%.0f grid_w=%.0f",
                self.instance_id, len(points), soc, total_pv, total_grid,
            )
            return points
        except Exception as exc:
            self.last_error = str(exc)
            log.warning("modbus read failed | instance=%s error=%s", self.instance_id, exc)
            raise

    def diagnostics(self) -> dict[str, Any]:
        return {"last_error": self.last_error, **self.last_diagnostics}

    def execute(self, command: str, parameters: dict[str, Any] | None = None):
        raise NotImplementedError("Victron GX V1 Shadow plugin is read-only")
