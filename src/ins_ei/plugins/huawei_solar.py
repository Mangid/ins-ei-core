from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from huawei_solar import create_device_instance, create_sub_device_instance, create_tcp_client
from huawei_solar import register_names as rn

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin

log = logging.getLogger("ins_ei.plugin.huawei_solar")


def _run(coro):
    return asyncio.run(coro)


def _as_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class HuaweiSolarPlugin(Plugin):
    """Huawei SUN2000/LUNA/Smart Meter adapter using huawei-solar-lib."""

    def __init__(self, instance_id: str, config: dict[str, Any]) -> None:
        super().__init__(instance_id, config)
        self.running = False
        self.last_error: str | None = None
        self.last_diagnostics: dict[str, Any] = {}

    def validate_config(self) -> None:
        if not str(self.config.get("host", "")).strip():
            raise ValueError("huawei_solar requires host")

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def health(self) -> PluginHealth:
        if not self.running:
            return PluginHealth(status=PluginStatus.STOPPED, message="plugin stopped")
        if self.last_error:
            return PluginHealth(status=PluginStatus.DEGRADED, message=self.last_error)
        if not self.last_diagnostics:
            return PluginHealth(status=PluginStatus.STARTING, message="waiting for Huawei telemetry")
        return PluginHealth(status=PluginStatus.RUNNING, message="Huawei Solar telemetry active")

    def _unit_ids(self) -> list[int]:
        raw = self.config.get("inverter_unit_ids", "1")
        if isinstance(raw, str):
            raw = [x.strip() for x in raw.split(",") if x.strip()]
        return [int(x) for x in raw]

    def _point(self, component: str, name: str, value: float, unit: str, now, source) -> Point:
        return Point(component_id=component, point=name, value=value, unit=unit,
                     quality=Quality.GOOD, observed_at=now, source=source)

    async def _collect(self) -> tuple[list[tuple[str, str, float, str]], dict[str, Any]]:
        host = str(self.config["host"])
        port = int(self.config.get("port", 502))
        timeout = int(float(self.config.get("timeout", 10)))
        units = self._unit_ids()
        primary = int(self.config.get("primary_unit_id", units[0]))
        client = create_tcp_client(host=host, port=port, unit_id=primary, timeout=timeout)
        await client.connect()
        try:
            device = await create_device_instance(client)
            devices = {primary: device}
            for unit in units:
                if unit != primary:
                    devices[unit] = await create_sub_device_instance(device, unit)

            values: list[tuple[str, str, float, str]] = []
            prefix = str(self.config.get("component_prefix") or self.instance_id)
            total_pv = 0.0
            models = {}
            for index, unit in enumerate(units, start=1):
                d = devices[unit]
                models[unit] = d.model_name
                input_power = float((await d.client.get(rn.INPUT_POWER)).value)
                active_power = float((await d.client.get(rn.ACTIVE_POWER)).value)
                total_pv += max(0.0, input_power)
                component = f"{prefix}_inverter_{index}"
                values += [
                    (component, "pv.generation_power", max(0.0, input_power), "W"),
                    (component, "power.output", active_power, "W"),
                ]
            values.append((f"{prefix}_pv", "pv.generation_power", total_pv, "W"))

            # Meter/storage are optional per Huawei host. This matters for plants with
            # multiple independently addressed inverters such as Kaufmann.
            if _as_bool(self.config.get("include_meter"), True):
                meter_power = float((await device.client.get(rn.POWER_METER_ACTIVE_POWER)).value)
                values += [
                    (f"{prefix}_grid", "grid.import_power", max(0.0, meter_power), "W"),
                    (f"{prefix}_grid", "grid.export_power", max(0.0, -meter_power), "W"),
                ]

            if _as_bool(self.config.get("include_battery"), True):
                soc = float((await device.client.get(rn.STORAGE_STATE_OF_CAPACITY)).value)
                battery_power = float((await device.client.get(rn.STORAGE_CHARGE_DISCHARGE_POWER)).value)
                values += [
                    (f"{prefix}_battery", "battery.soc", soc, "%"),
                    (f"{prefix}_battery", "battery.charge_power", max(0.0, battery_power), "W"),
                    (f"{prefix}_battery", "battery.discharge_power", max(0.0, -battery_power), "W"),
                ]
            diagnostics = {
                "transport": "huawei-solar-lib/3.0.7",
                "host": host, "port": port, "primary_unit_id": primary,
                "inverter_unit_ids": units, "models": models, "points": len(values),
            }
            return values, diagnostics
        finally:
            await client.disconnect()

    def read_points(self) -> list[Point]:
        if not self.running:
            return []
        try:
            raw, diagnostics = _run(self._collect())
            now = datetime.now().astimezone()
            source = Source(plugin_instance=self.instance_id)
            points = [
                self._point(component, name, value, unit, now, source)
                for component, name, value, unit in raw
            ]
            self.last_diagnostics = diagnostics
            self.last_error = None
            return points
        except Exception as exc:
            self.last_error = str(exc)
            log.warning("Huawei Solar read failed | instance=%s error=%s", self.instance_id, exc)
            raise

    def discover_components(self, points: list[Point]) -> list[dict[str, Any]]:
        present = {p.component_id for p in points}
        result = []
        prefix = str(self.config.get("component_prefix") or self.instance_id)
        for component_id, kind in [(f"{prefix}_pv", "PV"), (f"{prefix}_battery", "BATTERY"), (f"{prefix}_grid", "GRID_METER")]:
            if component_id in present:
                result.append({"id": component_id, "kind": kind, "ready": True})
        for component_id in sorted(x for x in present if x.startswith(f"{prefix}_inverter_")):
            result.append({"id": component_id, "kind": "PV_INVERTER", "ready": True})
        return result

    def diagnostics(self) -> dict[str, Any]:
        return {"last_error": self.last_error, **self.last_diagnostics}

    def execute(self, command: str, parameters: dict[str, Any] | None = None):
        raise NotImplementedError("Huawei Solar V1 remains read-only; control capabilities are not commissioned")
