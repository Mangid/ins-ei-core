from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentPresentation:
    role: str
    shape: str
    orientation: str = "horizontal"


PRESENTATION: dict[str, ComponentPresentation] = {
    "HEAT_GENERATOR": ComponentPresentation("source", "heat_generator"),
    "BUFFER": ComponentPresentation("storage", "tank", "vertical"),
    "DHW": ComponentPresentation("storage", "dhw_tank", "vertical"),
    "POWER_TO_HEAT": ComponentPresentation("converter", "electric_heater"),
    "PUMP": ComponentPresentation("transport", "pump"),
    "VALVE": ComponentPresentation("control", "valve"),
    "MIXER": ComponentPresentation("control", "mixer"),
    "HYDRAULIC_NODE": ComponentPresentation("junction", "node"),
    "HEATING_CIRCUIT": ComponentPresentation("consumer", "heating_circuit"),
    "HEAT_NETWORK": ComponentPresentation("network", "heat_network"),
    "HEAT_METER": ComponentPresentation("meter", "heat_meter"),
    "ELECTRIC_METER": ComponentPresentation("meter", "electric_meter"),
    "GRID": ComponentPresentation("source_sink", "grid"),
    "PV": ComponentPresentation("source", "pv"),
    "BATTERY": ComponentPresentation("storage", "battery"),
    "MARKET": ComponentPresentation("information", "market"),
    "FORECAST": ComponentPresentation("information", "forecast"),
    "WEATHER": ComponentPresentation("information", "weather"),
}


def presentation_for(kind: str) -> ComponentPresentation:
    return PRESENTATION.get(kind, ComponentPresentation("generic", "component"))
