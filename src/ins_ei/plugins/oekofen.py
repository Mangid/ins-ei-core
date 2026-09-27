from __future__ import annotations

from datetime import datetime
from typing import Any

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin
from ins_ei.plugins.oekofen_transport import OekofenTransport


def _raw(value: Any) -> Any:
    return value.get("val") if isinstance(value, dict) else value


def _number(value: Any, factor: float = 1.0) -> float | None:
    try:
        return float(_raw(value)) * factor
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str | None:
    value = _raw(value)
    return None if value is None else str(value)


class OekofenPlugin(Plugin):
    """ÖkoFEN device plugin: protocol + vendor semantics, never strategy."""

    def __init__(self, instance_id: str, config: dict[str, Any]) -> None:
        super().__init__(instance_id, config)
        self.transport: OekofenTransport | None = None
        self.running = False
        self.last_error: str | None = None
        self.last_unmapped: dict[str, Any] = {}

    def validate_config(self) -> None:
        for key in ("host", "password"):
            if not str(self.config.get(key, "")).strip():
                raise ValueError(f"oekofen plugin requires {key}")

    def start(self) -> None:
        self.transport = OekofenTransport(
            host=self.config["host"],
            password=self.config["password"],
            port=int(self.config.get("port", 4321)),
            timeout=float(self.config.get("timeout", 10.0)),
        )
        self.running = True

    def stop(self) -> None:
        self.running = False

    def health(self) -> PluginHealth:
        if not self.running:
            return PluginHealth(status=PluginStatus.STOPPED, message="plugin stopped")
        if self.last_error:
            return PluginHealth(status=PluginStatus.DEGRADED, message=self.last_error)
        return PluginHealth(status=PluginStatus.RUNNING, message="ÖkoFEN connected")

    def _component(self, role: str, default: str) -> str:
        return self.config.get("components", {}).get(role, default)

    def read_points(self) -> list[Point]:
        if not self.running or self.transport is None:
            return []
        try:
            data = self.transport.read_all()
            points, used = self._normalize(data)
            self.last_error = None
            self.last_unmapped = {
                f"{section}.{key}": _raw(value)
                for section, values in data.items()
                if isinstance(values, dict)
                for key, value in values.items()
                if (section, key) not in used
            }
            return points
        except Exception as exc:
            self.last_error = str(exc)
            raise

    def _normalize(self, data: dict) -> tuple[list[Point], set[tuple[str, str]]]:
        now = datetime.now().astimezone()
        source = Source(plugin_instance=self.instance_id)
        points: list[Point] = []
        used: set[tuple[str, str]] = set()

        def add(section: str, key: str, component: str, point: str, unit: str | None = None,
                factor: float = 1.0, text: bool = False) -> None:
            values = data.get(section)
            if not isinstance(values, dict) or key not in values:
                return
            used.add((section, key))
            value = _text(values[key]) if text else _number(values[key], factor)
            if value is not None:
                points.append(Point(
                    component_id=component, point=point, value=value, unit=unit,
                    quality=Quality.GOOD, observed_at=now, source=source,
                ))

        boiler = self._component("boiler", "pellet_boiler")
        buffer = self._component("buffer", "buffer")
        dhw = self._component("dhw", "dhw")
        weather = self._component("weather", "weather")

        add("system", "L_ambient", weather, "weather.outdoor_temperature", "°C", .1)
        add("system", "L_boiler_temp", boiler, "thermal.temperature", "°C", .1)
        add("pe1", "L_temp_act", boiler, "thermal.temperature", "°C", .1)
        add("pe1", "L_frt_temp_act", boiler, "thermal.flame_temperature", "°C", .1)
        add("pe1", "L_modulation", boiler, "power.modulation", "%")
        add("pe1", "L_br", boiler, "state.burner", text=True)
        add("pe1", "L_statetext", boiler, "state.operating", text=True)
        add("pe1", "mode", boiler, "state.operating_mode", text=True)

        add("pu1", "L_tpo_act", buffer, "thermal.temperature_upper", "°C", .1)
        add("pu1", "L_tpm_act", buffer, "thermal.temperature_lower", "°C", .1)
        add("pu1", "mintemp_off", buffer, "thermal.minimum_off_temperature", "°C", .1)
        add("pu1", "L_pump", buffer, "state.pump", text=True)
        add("pu1", "L_statetext", buffer, "state.operating", text=True)

        add("ww1", "L_ontemp_act", dhw, "thermal.temperature", "°C", .1)
        add("ww1", "L_temp_set", dhw, "thermal.target_temperature", "°C", .1)
        add("ww1", "L_offtemp_act", dhw, "thermal.temperature_bottom", "°C", .1)
        add("ww1", "L_pump", dhw, "state.pump", text=True)
        add("ww1", "L_statetext", dhw, "state.operating", text=True)
        add("ww1", "heat_once", dhw, "state.one_time_charge", text=True)

        for index in (1, 2):
            section = f"hk{index}"
            component = self._component(section, section)
            add(section, "L_flowtemp_act", component, "thermal.supply_temperature", "°C", .1)
            add(section, "L_flowtemp_set", component, "thermal.target_supply_temperature", "°C", .1)
            add(section, "L_pump", component, "state.pump", text=True)
            add(section, "L_statetext", component, "state.operating", text=True)

        return points, used

    def execute(self, command: str, parameters: dict[str, Any] | None = None) -> Any:
        if self.transport is None or not self.running:
            raise RuntimeError("OEKOFEN_NOT_RUNNING")
        parameters = parameters or {}
        if command == "heat_generator.set_enabled":
            enabled = bool(parameters["enabled"])
            return self.transport.set_value("pe1", "mode", 1 if enabled else 0)
        if command == "dhw.request_once":
            enabled = bool(parameters.get("enabled", True))
            return self.transport.set_value("ww1", "heat_once", "true" if enabled else "false")
        raise ValueError(f"OEKOFEN_COMMAND_UNSUPPORTED:{command}")

    def diagnostics(self) -> dict[str, Any]:
        return {
            "unmapped_count": len(self.last_unmapped),
            "unmapped": self.last_unmapped,
            "last_error": self.last_error,
        }
