from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin
from ins_ei.plugins.fronius_transport import FroniusTransport

log = logging.getLogger("ins_ei.plugin.fronius")



def _latest_archive_value(channel: Any) -> float | None:
    """Extract newest numeric Fronius archive sample from one channel."""
    if not isinstance(channel, dict):
        return None
    values = channel.get("Values")
    if isinstance(values, dict):
        candidates = []
        for key, value in values.items():
            try:
                candidates.append((int(key), float(value)))
            except (TypeError, ValueError):
                continue
        return max(candidates, key=lambda x: x[0])[1] if candidates else None
    if isinstance(values, list):
        for value in reversed(values):
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None

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
                pac_value = max(0.0, float(pac))
                points.append(Point(
                    component_id=f"{prefix}_pv", point="pv.generation_power",
                    value=pac_value, unit="W", quality=Quality.GOOD,
                    observed_at=now, source=source,
                ))
                # The physical inverter remains a distinct component while the
                # logical PV component can be aggregated separately.
                points.append(Point(
                    component_id=f"{prefix}_inverter", point="pv.generation_power",
                    value=pac_value, unit="W", quality=Quality.GOOD,
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


            # Optional per-input/string archive telemetry. The plugin exposes
            # generic PV inputs only; orientation/roof semantics belong to Site commissioning.
            archive_error = None
            try:
                archive = self.transport.archive_strings_today()
                archive_data = archive.get("Body", {}).get("Data", {})
                inverter_archive = archive_data.get(f"inverter/{device_id}", {})
                channels = inverter_archive.get("Data", {}) if isinstance(inverter_archive, dict) else {}
                for input_no in (1, 2):
                    current = _latest_archive_value(channels.get(f"Current_DC_String_{input_no}"))
                    voltage = _latest_archive_value(channels.get(f"Voltage_DC_String_{input_no}"))
                    component = f"{prefix}_input_{input_no}"
                    if current is not None:
                        points.append(Point(component_id=component, point="electrical.current_dc", value=current, unit="A", quality=Quality.GOOD, observed_at=now, source=source))
                    if voltage is not None:
                        points.append(Point(component_id=component, point="electrical.voltage_dc", value=voltage, unit="V", quality=Quality.GOOD, observed_at=now, source=source))
                    if current is not None and voltage is not None:
                        points.append(Point(component_id=component, point="pv.generation_power", value=max(0.0, current * voltage), unit="W", quality=Quality.GOOD, observed_at=now, source=source))
            except Exception as exc:
                archive_error = str(exc)
                log.info("archive string telemetry unavailable | instance=%s error=%s", self.instance_id, exc)

            flow = self.transport.power_flow()
            flow_data = flow.get("Body", {}).get("Data", {})
            three_phase = self.transport.inverter_three_phase(device_id).get("Body", {}).get("Data", {})
            cumulation = self.transport.inverter_cumulation(device_id).get("Body", {}).get("Data", {})
            minmax = self.transport.inverter_minmax(device_id).get("Body", {}).get("Data", {})
            self.last_diagnostics = {
                "device_id": device_id,
                "component_prefix": prefix,
                "powerflow_version": flow_data.get("Version"),
                "powerflow_keys": sorted(flow_data.keys()),
                "inverter_keys": sorted(body.keys()),
                "three_phase_keys": sorted(three_phase.keys()),
                "cumulation_keys": sorted(cumulation.keys()),
                "minmax_keys": sorted(minmax.keys()),
                "archive_error": archive_error,
                "points": len(points),
            }
            self.last_error = None
            log.info(
                "solar api telemetry | instance=%s points=%d common=%s three_phase=%s cumulation=%s minmax=%s",
                self.instance_id, len(points), sorted(body.keys()), sorted(three_phase.keys()),
                sorted(cumulation.keys()), sorted(minmax.keys()),
            )
            return points
        except Exception as exc:
            self.last_error = str(exc)
            log.warning("solar api read failed | instance=%s error=%s", self.instance_id, exc)
            raise


    def discover_components(self, points: list[Point]) -> list[dict[str, Any]]:
        prefix = str(self.config.get("component_prefix") or self.instance_id)
        present = {p.component_id for p in points}
        result = []
        candidates = [
            (f"{prefix}_pv", "PV"),
            (f"{prefix}_inverter", "PV_INVERTER"),
            (f"{prefix}_input_1", "PV_INPUT"),
            (f"{prefix}_input_2", "PV_INPUT"),
        ]
        for component_id, kind in candidates:
            if component_id in present:
                result.append({"id": component_id, "kind": kind, "ready": True})
        return result

    def diagnostics(self) -> dict[str, Any]:
        return {"last_error": self.last_error, **self.last_diagnostics}

    def execute(self, command: str, parameters: dict[str, Any] | None = None):
        raise NotImplementedError("Fronius V1 plugin is read-only")
