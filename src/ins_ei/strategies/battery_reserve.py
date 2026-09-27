from __future__ import annotations

from dataclasses import dataclass

from ins_ei.strategy import Confidence, Priority, Proposal, StrategyContext


@dataclass
class BatteryReserveStrategy:
    """Protect a configured minimum battery SOC from optimization actions."""

    battery_component: str
    minimum_soc_percent: float
    id: str = "battery_reserve"
    priority: Priority = Priority.SAFETY

    def evaluate(self, context: StrategyContext) -> Proposal | None:
        soc = context.good_value(self.battery_component, "battery.soc")
        if soc is None:
            return Proposal(
                strategy=self.id,
                action="BLOCK_BATTERY_DISCHARGE",
                priority=self.priority,
                reason="Battery SOC is unavailable or stale; discharge optimization is blocked.",
                confidence=Confidence.HIGH,
                evidence={"soc_available": False},
            )
        soc = float(soc)
        if soc > self.minimum_soc_percent:
            return None
        return Proposal(
            strategy=self.id,
            action="BLOCK_BATTERY_DISCHARGE",
            priority=self.priority,
            reason=(
                f"Battery SOC {soc:.1f}% is at/below reserve "
                f"{self.minimum_soc_percent:.1f}%."
            ),
            confidence=Confidence.HIGH,
            evidence={
                "soc_percent": soc,
                "minimum_soc_percent": self.minimum_soc_percent,
            },
        )
