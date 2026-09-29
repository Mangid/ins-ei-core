from __future__ import annotations

from datetime import datetime
from typing import Any

from ins_ei.models import Point, Quality, Source


class ThermalShadow:
    """Generic, read-only thermal action recommender."""

    def __init__(self, graph, state) -> None:
        self.graph = graph
        self.state = state

    def _constraint(self, constraint_id: str):
        for c in self.graph.constraints:
            if c.id == constraint_id:
                return c
        return None

    def evaluate(self) -> list[Point]:
        now = datetime.now().astimezone()
        source = Source(plugin_instance="thermal-shadow")
        result: list[Point] = []

        dhw = self.state.get("dhw", "thermal.temperature", now)
        minimum = self._constraint("dhw_min_temperature")
        comfort = self._constraint("dhw_comfort_temperature")
        if dhw is None or dhw.quality != Quality.GOOD or minimum is None:
            dhw_action: Any = "HOLD_DATA_OR_CONSTRAINT_MISSING"
        elif float(dhw.value) < float(minimum.value):
            dhw_action = "DHW_HEAT_ONCE"
        elif comfort is not None and float(dhw.value) >= float(comfort.value):
            dhw_action = "HOLD_COMFORT_OK"
        else:
            dhw_action = "HOLD_FORECAST_PENDING"
        result.append(Point(
            component_id="dhw", point="decision.dhw", value=dhw_action, unit=None,
            quality=Quality.GOOD, observed_at=now, source=source,
        ))

        # V1 intentionally does not invent a buffer reserve threshold.
        buffer_min = self._constraint("buffer_min_temperature")
        buffer = self.state.get("buffer", "thermal.temperature_upper", now)
        if buffer_min is None:
            generator_action = "HOLD_INSUFFICIENT_CONSTRAINTS"
        elif buffer is None or buffer.quality != Quality.GOOD:
            generator_action = "HOLD_DATA_MISSING"
        elif float(buffer.value) < float(buffer_min.value):
            generator_action = "HEAT_GENERATOR_ENABLE"
        else:
            generator_action = "HOLD"
        result.append(Point(
            component_id="pellet_boiler", point="decision.heat_generator",
            value=generator_action, unit=None, quality=Quality.GOOD,
            observed_at=now, source=source,
        ))
        return result
