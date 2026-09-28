from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin
from ins_ei.plugins.victron_modbus_transport import VictronModbusTransport

log = logging.getLogger("ins_ei.plugin.victron_gx")


class VictronGXPlugin(Plugin):
    """Read-only local Victron GX Modbus TCP adapter."""

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
            self.config["host"],
            int(self.config.get("port", 502)),
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

    def read_points(self) -> list[Point]:
        if not self.running or self.transport is None:
            return []

        # V1 probe: GX system service is officially Unit-ID 100.
        # We intentionally do not hard-code battery/PV device Unit-IDs here:
        # those depend on the GX available-services mapping.
        try:
            unit_id = int(self.config.get("system_unit_id", 100))
            # Probe a single documented system-service register range only to
            # prove GX Modbus reachability. Canonical battery/PV mappings are
            # added after service discovery on the actual GX.
            words = self.transport.read_registers(unit_id, 800, 1)
            self.last_diagnostics = {
                "system_unit_id": unit_id,
                "probe_register": 800,
                "probe_value": words[0],
                "transport": "modbus_tcp",
            }
            self.last_error = None
            log.info("modbus reachable | instance=%s unit_id=%d probe=800 value=%d",
                     self.instance_id, unit_id, words[0])
            return []
        except Exception as exc:
            self.last_error = str(exc)
            log.warning("modbus read failed | instance=%s error=%s", self.instance_id, exc)
            raise

    def diagnostics(self) -> dict[str, Any]:
        return {"last_error": self.last_error, **self.last_diagnostics}

    def execute(self, command: str, parameters: dict[str, Any] | None = None):
        raise NotImplementedError("Victron GX V1 Shadow plugin is read-only")
