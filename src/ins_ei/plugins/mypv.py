from __future__ import annotations

from datetime import datetime
from typing import Any

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin
from ins_ei.plugins.mypv_transport import MyPVTransport


class MyPVPlugin(Plugin):
    """my-PV AC-THOR family plugin: device knowledge only."""

    def __init__(self, instance_id: str, config: dict[str, Any]) -> None:
        super().__init__(instance_id, config)
        self.transport: MyPVTransport | None = None
        self.running = False
        self.last_error: str | None = None
        self.last_unmapped: dict[str, Any] = {}

    def validate_config(self) -> None:
        if not str(self.config.get("host", "")).strip():
            raise ValueError("mypv plugin requires host")

    def start(self) -> None:
        self.transport = MyPVTransport(
            host=self.config["host"],
            port=int(self.config.get("port", 502)),
            unit_id=int(self.config.get("unit_id", 1)),
            timeout=float(self.config.get("timeout", 5.0)),
            http_enabled=bool(self.config.get("http_enabled", True)),
        )
        self.running = True

    def stop(self) -> None:
        self.running = False

    def health(self) -> PluginHealth:
        if not self.running:
            return PluginHealth(status=PluginStatus.STOPPED, message="plugin stopped")
        if self.last_error:
            return PluginHealth(status=PluginStatus.DEGRADED, message=self.last_error)
        return PluginHealth(status=PluginStatus.RUNNING, message="my-PV connected")

    def read_points(self) -> list[Point]:
        if not self.running or self.transport is None:
            return []
        try:
            raw = self.transport.read()
            points = self._normalize(raw)
            self.last_unmapped = self._unmapped(raw)
            self.last_error = None
            return points
        except Exception as exc:
            self.last_error = str(exc)
            raise

    def _normalize(self, raw: dict[str, Any]) -> list[Point]:
        component = self.config.get("component_id", "power_to_heat")
        now = datetime.now().astimezone()
        source = Source(plugin_instance=self.instance_id)
        points: list[Point] = []

        mapping = {
            "device_power_w": ("power.electrical", "W"),
            "max_possible_power_w": ("power.maximum_available", "W"),
            "power_out1_w": ("power.output_l1", "W"),
            "power_out2_w": ("power.output_l2", "W"),
            "power_out3_w": ("power.output_l3", "W"),
            "voltage_l1_v": ("electrical.voltage_l1", "V"),
            "voltage_l2_v": ("electrical.voltage_l2", "V"),
            "voltage_l3_v": ("electrical.voltage_l3", "V"),
            "current_l1_a": ("electrical.current_l1", "A"),
            "current_l2_a": ("electrical.current_l2", "A"),
            "current_l3_a": ("electrical.current_l3", "A"),
            "frequency_hz": ("electrical.frequency", "Hz"),
            "operation_state": ("state.operating", None),
            "operation_mode": ("state.mode", None),
            "device_state": ("state.device", None),
            "relay1_status": ("state.relay1", None),
        }
        for raw_key, (point_name, unit) in mapping.items():
            value = raw.get(raw_key)
            if value is not None:
                points.append(Point(
                    component_id=component, point=point_name, value=value, unit=unit,
                    quality=Quality.GOOD, observed_at=now, source=source,
                ))
        return points

    @staticmethod
    def _unmapped(raw: dict[str, Any]) -> dict[str, Any]:
        mapped = {
            "device_power_w", "max_possible_power_w", "power_out1_w", "power_out2_w",
            "power_out3_w", "voltage_l1_v", "voltage_l2_v", "voltage_l3_v",
            "current_l1_a", "current_l2_a", "current_l3_a", "frequency_hz",
            "operation_state", "operation_mode", "device_state", "relay1_status",
        }
        result = {key: value for key, value in raw.items() if key not in mapped and key != "http" and value is not None}
        result.update({f"http.{key}": value for key, value in (raw.get("http") or {}).items()})
        return result

    def diagnostics(self) -> dict[str, Any]:
        return {
            "unmapped_count": len(self.last_unmapped),
            "unmapped": self.last_unmapped,
            "last_error": self.last_error,
        }

    def execute(self, command: str, parameters: dict[str, Any] | None = None) -> Any:
        # We intentionally do not guess/write undocumented control registers.
        # A proven write transport will be added separately before control is enabled.
        raise NotImplementedError(f"my-PV command not enabled yet: {command}")
