from __future__ import annotations

from dataclasses import dataclass

from ins_ei.strategy import Confidence, Intent, Priority, Proposal, StrategyContext


@dataclass
class ThermalSurplusStorageStrategy:
    """Store available electrical export surplus as heat.

    This strategy is vendor-neutral. It reads canonical grid export and thermal
    storage temperature, then proposes a canonical power-to-heat command.
    """

    grid_component: str
    storage_component: str
    temperature_point: str
    max_temperature_c: float
    power_to_heat_component: str
    max_power_w: float
    reserve_export_w: float = 100.0
    minimum_power_w: float = 100.0
    id: str = "thermal_surplus_storage"
    priority: Priority = Priority.OPTIMIZATION

    def evaluate(self, context: StrategyContext) -> Proposal | None:
        export_power = context.good_value(self.grid_component, "grid.export_power")
        temperature = context.good_value(self.storage_component, self.temperature_point)

        if export_power is None or temperature is None:
            return None

        export_power = max(0.0, float(export_power))
        temperature = float(temperature)

        if temperature >= self.max_temperature_c:
            return None

        usable_surplus = max(0.0, export_power - self.reserve_export_w)
        requested_power = min(usable_surplus, self.max_power_w)

        if requested_power < self.minimum_power_w:
            return None

        return Proposal(
            strategy=self.id,
            action="STORE_ELECTRICAL_SURPLUS_AS_HEAT",
            priority=self.priority,
            reason=(
                f"Grid export {export_power:.0f} W is available while "
                f"{self.storage_component} is {temperature:.1f} °C below "
                f"maximum {self.max_temperature_c:.1f} °C; request "
                f"{requested_power:.0f} W power-to-heat."
            ),
            confidence=Confidence.HIGH,
            intents=(
                Intent(
                    target=self.power_to_heat_component,
                    command="power_to_heat.set_power",
                    parameters={"power_w": round(requested_power)},
                ),
            ),
            evidence={
                "grid_export_w": export_power,
                "reserve_export_w": self.reserve_export_w,
                "usable_surplus_w": usable_surplus,
                "storage_temperature_c": temperature,
                "storage_max_temperature_c": self.max_temperature_c,
                "requested_power_w": requested_power,
            },
        )
