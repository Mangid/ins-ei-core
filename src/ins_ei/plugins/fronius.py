from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin
from ins_ei.plugins.fronius_transport import FroniusTransport

log = logging.getLogger("ins_ei.plugin.fronius")


def _value(node):
    if isinstance(node, dict):
        return node.get("Value")
    return node


class FroniusPlugin(Plugin):
    """Generic read-only Fronius Solar API provider."""

    def __init__(self, instance_id: str, config: dict[str, Any]) -> None:
        super().__init__(instance_id, config)
        self.transport: FroniusTransport | None = None
        self.running = False
        self.last_error: str | None = None
        self.last_diagnostics: dict[str, Any] = {}

    def validate_config(self) -> None:
        if not str(self.config.get("host", "")).strip():
            raise ValueError("fronius requires host")

    def start(self) -> None:
        self.transport = FroniusTransport(
            self.config["host"], float(self.config.get("timeout", 5.0))
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
            return PluginHealth(status=PluginStatus.STARTING, message="waiting for Solar API telemetry")
        return PluginHealth(status=PluginStatus.RUNNING, message="Fronius Solar API telemetry active")

    def read_points(self) -> list[Point]:
        if not self.running or self.transport is None:
            return []
        try:
            device_id = int(self.config.get("device_id", 1))
            prefix = str(self.config.get("component_prefix") or self.instance_id)
            common = self.transport.inverter_common(device_id)
            body = common.get("Body", {}).get("Data", {})
            now = datetime.now().astimezone()
            source = Source(plugin_instance=self.instance_id)
            points = []

            pac = _value(body.get("PAC"))
            if pac is not None:
                points.append(Point(
                    component_id=f"{prefix}_pv", point="pv.generation_power",
                    value=max(0.0, float(pac)), unit="W", quality=Quality.GOOD,
                    observed_at=now, source=source,
                ))

            uac = _value(body.get("UAC"))
            iac = _value(body.get("IAC"))
            fac = _value(body.get("FAC"))
            udc = _value(body.get("UDC"))
            idc = _value(body.get("IDC"))
            mappings = [
                (uac, "electrical.voltage_l1", "V"),
                (iac, "electrical.current_l1", "A"),
                (fac, "electrical.frequency", "Hz"),
                (udc, "electrical.voltage_dc", "V"),
                (idc, "electrical.current_dc", "A"),
            ]
            for value, point, unit in mappings:
                if value is not None:
                    points.append(Point(
                        component_id=f"{prefix}_inverter", point=point,
                        value=float(value), unit=unit, quality=Quality.GOOD,
                        observed_at=now, source=source,
                    ))

            flow = self.transport.power_flow()
            flow_data = flow.get("Body", {}).get("Data", {})
            self.last_diagnostics = {
                "device_id": device_id,
                "component_prefix": prefix,
                "powerflow_version": flow_data.get("Version"),
                "powerflow_keys": sorted(flow_data.keys()),
                "inverter_keys": sorted(body.keys()),
                "points": len(points),
            }
            self.last_error = None
            log.info(
                "solar api telemetry | instance=%s points=%d inverter_keys=%d powerflow_keys=%d",
                self.instance_id, len(points), len(body), len(flow_data),
            )
            return points
        except Exception as exc:
            self.last_error = str(exc)
            log.warning("solar api read failed | instance=%s error=%s", self.instance_id, exc)
            raise

    def diagnostics(self) -> dict[str, Any]:
        return {"last_error": self.last_error, **self.last_diagnostics}

    def execute(self, command: str, parameters: dict[str, Any] | None = None):
        raise NotImplementedError("Fronius V1 plugin is read-only")
