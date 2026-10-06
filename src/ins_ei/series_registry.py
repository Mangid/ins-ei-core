from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeriesDefinition:
    name: str
    unit: str
    description: str


SERIES = {
    "market.import_price": SeriesDefinition(
        "market.import_price", "ct/kWh", "Gross electricity import price per time slot."
    ),
    "market.export_price": SeriesDefinition(
        "market.export_price", "ct/kWh", "Gross/net-defined export remuneration per time slot according to site tariff model."
    ),
    "forecast.pv_energy": SeriesDefinition(
        "forecast.pv_energy", "kWh", "Forecast PV energy produced during the slot."
    ),
    "forecast.battery_soc": SeriesDefinition(\n        "forecast.battery_soc", "%", "Baseline forecast battery state of charge at end of slot."\n    ),\n    "forecast.consumption_energy": SeriesDefinition(
        "forecast.consumption_energy", "kWh", "Forecast site electrical consumption during the slot."
    ),
}


def series_definition(name: str) -> SeriesDefinition | None:
    return SERIES.get(name)


def validate_series(name: str, unit: str) -> None:
    spec = series_definition(name)
    if spec is None:
        raise ValueError(f"SERIES_UNKNOWN:{name}")
    if spec.unit != unit:
        raise ValueError(f"SERIES_UNIT:{name}:expected={spec.unit}:got={unit}")
