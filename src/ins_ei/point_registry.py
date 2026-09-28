from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PointDefinition:
    name: str
    unit: str | None
    value_type: type
    stale_after_seconds: float
    description: str


_DEFINITIONS = [
    # Grid / electrical flow: fast-changing control inputs.
    PointDefinition("grid.import_power", "W", float, 10, "Active grid import power, non-negative."),
    PointDefinition("grid.export_power", "W", float, 10, "Active grid export power, non-negative."),
    PointDefinition("energy.import_total", "kWh", float, 300, "Cumulative imported electrical energy."),
    PointDefinition("energy.export_total", "kWh", float, 300, "Cumulative exported electrical energy."),
    PointDefinition("power.electrical", "W", float, 15, "Current active electrical power."),
    PointDefinition("power.maximum_available", "W", float, 60, "Currently reported maximum available power."),
    PointDefinition("power.output_l1", "W", float, 15, "Active output power phase/channel 1."),
    PointDefinition("power.output_l2", "W", float, 15, "Active output power phase/channel 2."),
    PointDefinition("power.output_l3", "W", float, 15, "Active output power phase/channel 3."),
    PointDefinition("power.modulation", "%", float, 30, "Current device modulation."),
    PointDefinition("electrical.voltage_l1", "V", float, 30, "Voltage phase 1."),
    PointDefinition("electrical.voltage_l2", "V", float, 30, "Voltage phase 2."),
    PointDefinition("electrical.voltage_l3", "V", float, 30, "Voltage phase 3."),
    PointDefinition("electrical.current_l1", "A", float, 30, "Current phase 1."),
    PointDefinition("electrical.current_l2", "A", float, 30, "Current phase 2."),
    PointDefinition("electrical.current_l3", "A", float, 30, "Current phase 3."),
    PointDefinition("electrical.frequency", "Hz", float, 30, "Electrical frequency."),
    PointDefinition("electrical.voltage_dc", "V", float, 30, "DC bus/device voltage."),
    PointDefinition("electrical.current_dc", "A", float, 30, "Signed DC current; positive/negative direction is provider-defined diagnostics unless paired with canonical flow points."),

    # PV and battery: fast control state plus slower capacity information.
    PointDefinition("pv.generation_power", "W", float, 15, "Current PV generation power, non-negative."),
    PointDefinition("battery.soc", "%", float, 30, "Battery state of charge from 0 to 100 percent."),
    PointDefinition("battery.charge_power", "W", float, 15, "Current battery charging power, non-negative."),
    PointDefinition("battery.discharge_power", "W", float, 15, "Current battery discharging power, non-negative."),
    PointDefinition("battery.max_charge_power", "W", float, 60, "Current permitted/available maximum battery charge power."),
    PointDefinition("battery.max_discharge_power", "W", float, 60, "Current permitted/available maximum battery discharge power."),
    PointDefinition("battery.capacity_usable", "kWh", float, 3600, "Configured/reported usable battery capacity."),
    PointDefinition("battery.energy_available", "kWh", float, 60, "Estimated usable energy currently available above zero/reference."),
    PointDefinition("battery.energy_free", "kWh", float, 60, "Estimated currently free usable battery capacity."),

    # Thermal state changes more slowly than electrical power.
    PointDefinition("thermal.temperature", "°C", float, 180, "Generic component temperature."),
    PointDefinition("thermal.temperature_upper", "°C", float, 180, "Upper storage temperature."),
    PointDefinition("thermal.temperature_lower", "°C", float, 180, "Lower storage temperature."),
    PointDefinition("thermal.temperature_bottom", "°C", float, 180, "Bottom/DHW lower temperature."),
    PointDefinition("thermal.target_temperature", "°C", float, 300, "Configured target temperature."),
    PointDefinition("thermal.minimum_off_temperature", "°C", float, 300, "Configured minimum/off temperature."),
    PointDefinition("thermal.supply_temperature", "°C", float, 120, "Current supply/flow temperature."),
    PointDefinition("thermal.target_supply_temperature", "°C", float, 300, "Target supply/flow temperature."),
    PointDefinition("thermal.flame_temperature", "°C", float, 60, "Combustion/flame temperature."),

    # Market: current tariff/price state. Slot-aware forecasts follow separately.
    PointDefinition("market.import_price", "ct/kWh", float, 3900, "Current gross electricity import price."),
    PointDefinition("market.export_price", "ct/kWh", float, 3900, "Current gross electricity export remuneration."),

    # Weather can be slower.
    PointDefinition("weather.outdoor_temperature", "°C", float, 600, "Outdoor air temperature."),

    # State points.
    PointDefinition("state.operating", None, object, 120, "Generic operating state."),
    PointDefinition("state.operating_mode", None, object, 300, "Configured operating mode."),
    PointDefinition("state.mode", None, object, 300, "Configured device mode."),
    PointDefinition("state.device", None, object, 120, "Device state."),
    PointDefinition("state.burner", None, object, 60, "Burner state."),
    PointDefinition("state.pump", None, object, 60, "Pump state."),
    PointDefinition("state.relay1", None, object, 60, "Relay 1 state."),
    PointDefinition("state.one_time_charge", None, object, 60, "One-time DHW charge state."),
]

POINTS: dict[str, PointDefinition] = {definition.name: definition for definition in _DEFINITIONS}


def definition(name: str) -> PointDefinition | None:
    return POINTS.get(name)


def validate_point(name: str, value: Any, unit: str | None) -> list[str]:
    spec = definition(name)
    if spec is None:
        return [f"POINT_UNKNOWN:{name}"]

    errors: list[str] = []
    if spec.unit != unit:
        errors.append(f"POINT_UNIT:{name}:expected={spec.unit}:got={unit}")

    if spec.value_type is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"POINT_TYPE:{name}:expected=number")
    elif spec.value_type is not object and not isinstance(value, spec.value_type):
        errors.append(f"POINT_TYPE:{name}:expected={spec.value_type.__name__}")
    return errors
