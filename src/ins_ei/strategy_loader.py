from __future__ import annotations

from typing import Any, Callable

from ins_ei.config import SiteConfig
from ins_ei.site_graph import SiteGraph
from ins_ei.strategy import StrategyEngine, StrategyModule
from ins_ei.strategies import DhwMinimumStrategy


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


STRATEGY_FACTORIES: dict[str, StrategyFactory] = {
    "dhw_minimum": build_dhw_minimum,
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
