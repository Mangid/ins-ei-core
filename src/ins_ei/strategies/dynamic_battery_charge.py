from __future__ import annotations

from dataclasses import dataclass

from ins_ei.strategy import Confidence, Intent, Priority, Proposal, StrategyContext


@dataclass
class DynamicBatteryChargeStrategy:
    """Rule-based grid charging at an attractive current import price.

    Forecast-aware multi-slot optimization intentionally belongs to a later
    optimizer. This module remains transparent and deterministic.
    """

    battery_component: str
    market_component: str
    max_import_price_ct_kwh: float
    target_soc_percent: float
    max_charge_power_w: float
    minimum_charge_power_w: float = 100.0
    id: str = "dynamic_battery_charge"
    priority: Priority = Priority.OPTIMIZATION

    def evaluate(self, context: StrategyContext) -> Proposal | None:
        soc = context.good_value(self.battery_component, "battery.soc")
        price = context.good_value(self.market_component, "market.import_price")
        device_limit = context.good_value(
            self.battery_component, "battery.max_charge_power"
        )

        if soc is None or price is None or device_limit is None:
            return None

        soc = float(soc)
        price = float(price)
        device_limit = max(0.0, float(device_limit))

        if soc >= self.target_soc_percent:
            return None
        if price > self.max_import_price_ct_kwh:
            return None

        requested_power = min(self.max_charge_power_w, device_limit)
        if requested_power < self.minimum_charge_power_w:
            return None

        return Proposal(
            strategy=self.id,
            action="GRID_CHARGE_BATTERY",
            priority=self.priority,
            reason=(
                f"Import price {price:.2f} ct/kWh is at/below configured "
                f"charge threshold {self.max_import_price_ct_kwh:.2f} ct/kWh "
                f"and battery SOC {soc:.1f}% is below target "
                f"{self.target_soc_percent:.1f}%."
            ),
            confidence=Confidence.HIGH,
            intents=(
                Intent(
                    target=self.battery_component,
                    command="battery.set_charge_power",
                    parameters={"power_w": round(requested_power)},
                ),
            ),
            evidence={
                "import_price_ct_kwh": price,
                "max_import_price_ct_kwh": self.max_import_price_ct_kwh,
                "soc_percent": soc,
                "target_soc_percent": self.target_soc_percent,
                "device_max_charge_power_w": device_limit,
                "configured_max_charge_power_w": self.max_charge_power_w,
                "requested_power_w": requested_power,
            },
        )
