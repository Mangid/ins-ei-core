from __future__ import annotations

from dataclasses import dataclass

from ins_ei.strategy import Confidence, Intent, Priority, Proposal, StrategyContext


@dataclass
class DhwMinimumStrategy:
    """Reusable mandatory DHW rule.

    This module knows no ÖkoFEN API. The site configuration chooses the DHW
    component, heat source and canonical command.
    """

    dhw_component: str
    temperature_point: str
    minimum_c: float
    heat_source: str
    command: str = "dhw.request_once"
    id: str = "dhw_minimum"
    priority: Priority = Priority.MANDATORY

    def evaluate(self, context: StrategyContext) -> Proposal | None:
        temperature = context.good_value(self.dhw_component, self.temperature_point)
        if temperature is None:
            return None
        temperature = float(temperature)
        if temperature >= self.minimum_c:
            return None
        return Proposal(
            strategy=self.id,
            action="REQUEST_DHW_HEAT",
            priority=self.priority,
            reason=(
                f"DHW temperature {temperature:.1f} °C is below configured "
                f"minimum {self.minimum_c:.1f} °C."
            ),
            confidence=Confidence.HIGH,
            intents=(
                Intent(
                    target=self.heat_source,
                    command=self.command,
                    parameters={"enabled": True},
                ),
            ),
            evidence={
                "temperature_c": temperature,
                "minimum_c": self.minimum_c,
                "dhw_component": self.dhw_component,
            },
        )
