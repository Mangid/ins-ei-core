from __future__ import annotations

from typing import Any, Callable

from ins_ei.config import SiteConfig
from ins_ei.site_graph import SiteGraph
from ins_ei.strategy import StrategyEngine, StrategyModule
from ins_ei.strategies import DhwMinimumStrategy, ThermalSurplusStorageStrategy, BatteryReserveStrategy, DynamicBatteryChargeStrategy


StrategyFactory = Callable[[dict[str, Any], SiteGraph], StrategyModule]


def _require_component(graph: SiteGraph, component_id: str, expected_kind: str | None = None) -> None:
    component = graph.component(component_id)
    if expected_kind and component.kind != expected_kind:
        raise ValueError(
            f"STRATEGY_COMPONENT_KIND:{component_id}:{component.kind}:expected={expected_kind}"
        )


def build_dhw_minimum(config: dict[str, Any], graph: SiteGraph) -> DhwMinimumStrategy:
    dhw = str(config["dhw_component"])
    heat_source = str(config["heat_source"])
    _require_component(graph, dhw, "DHW")
    _require_component(graph, heat_source)

    if heat_source not in {c.id for c in graph.sources(dhw, "HEATS")}:
        raise ValueError(f"STRATEGY_HEAT_SOURCE_NOT_CONNECTED:{heat_source}:{dhw}")

    return DhwMinimumStrategy(
        dhw_component=dhw,
        temperature_point=str(config.get("temperature_point", "thermal.temperature")),
        minimum_c=float(config["minimum_c"]),
        heat_source=heat_source,
        command=str(config.get("command", "dhw.request_once")),
    )


def build_thermal_surplus_storage(config: dict[str, Any], graph: SiteGraph) -> ThermalSurplusStorageStrategy:
    grid = str(config["grid_component"])
    storage = str(config["storage_component"])
    heater = str(config["power_to_heat_component"])

    _require_component(graph, grid, "GRID")
    _require_component(graph, storage)
    _require_component(graph, heater, "POWER_TO_HEAT")

    if heater not in {c.id for c in graph.targets(grid, "SUPPLIES")}:
        raise ValueError(f"STRATEGY_GRID_NOT_SUPPLYING_P2H:{grid}:{heater}")
    if storage not in {c.id for c in graph.targets(heater, "HEATS")}:
        raise ValueError(f"STRATEGY_P2H_NOT_HEATING_STORAGE:{heater}:{storage}")

    return ThermalSurplusStorageStrategy(
        grid_component=grid,
        storage_component=storage,
        temperature_point=str(config.get("temperature_point", "thermal.temperature_upper")),
        max_temperature_c=float(config["max_temperature_c"]),
        power_to_heat_component=heater,
        max_power_w=float(config["max_power_w"]),
        reserve_export_w=float(config.get("reserve_export_w", 100)),
        minimum_power_w=float(config.get("minimum_power_w", 100)),
    )


def build_battery_reserve(config: dict[str, Any], graph: SiteGraph) -> BatteryReserveStrategy:
    battery = str(config["battery_component"])
    _require_component(graph, battery, "BATTERY")
    minimum = float(config["minimum_soc_percent"])
    if not 0 <= minimum <= 100:
        raise ValueError("STRATEGY_BATTERY_RESERVE_RANGE")
    return BatteryReserveStrategy(
        battery_component=battery,
        minimum_soc_percent=minimum,
    )


def build_dynamic_battery_charge(config: dict[str, Any], graph: SiteGraph) -> DynamicBatteryChargeStrategy:
    battery = str(config["battery_component"])
    market = str(config["market_component"])
    _require_component(graph, battery, "BATTERY")
    _require_component(graph, market, "MARKET")

    target_soc = float(config["target_soc_percent"])
    if not 0 < target_soc <= 100:
        raise ValueError("STRATEGY_BATTERY_TARGET_SOC_RANGE")

    return DynamicBatteryChargeStrategy(
        battery_component=battery,
        market_component=market,
        max_import_price_ct_kwh=float(config["max_import_price_ct_kwh"]),
        target_soc_percent=target_soc,
        max_charge_power_w=float(config["max_charge_power_w"]),
        minimum_charge_power_w=float(config.get("minimum_charge_power_w", 100)),
    )


STRATEGY_FACTORIES: dict[str, StrategyFactory] = {
    "dhw_minimum": build_dhw_minimum,
    "thermal_surplus_storage": build_thermal_surplus_storage,
    "battery_reserve": build_battery_reserve,
    "dynamic_battery_charge": build_dynamic_battery_charge,
}


def build_strategy_engine(site: SiteConfig, graph: SiteGraph) -> StrategyEngine:
    modules: list[StrategyModule] = []
    strategy = site.strategy or {}

    for entry in strategy.get("modules", []):
        if not entry.get("enabled", True):
            continue
        module_id = str(entry.get("id", ""))
        if module_id not in STRATEGY_FACTORIES:
            raise ValueError(f"STRATEGY_UNKNOWN:{module_id}")
        config = dict(entry.get("config") or {})
        modules.append(STRATEGY_FACTORIES[module_id](config, graph))

    return StrategyEngine(modules)
