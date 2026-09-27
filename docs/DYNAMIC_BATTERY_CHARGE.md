# Dynamic Battery Charge Strategy

## Goal

Charge a battery from the grid when the current dynamic import price is sufficiently attractive and the battery is below a configured target SOC.

V0.1 is deliberately rule-based and explainable. It is **not** yet the multi-slot optimizer.

## Required canonical inputs

- `battery.soc`
- `battery.max_charge_power`
- `market.import_price`

All must be fresh/GOOD.

## Configuration

Example:

```yaml
- id: battery_reserve
  config:
    battery_component: battery
    minimum_soc_percent: 20

- id: dynamic_battery_charge
  config:
    battery_component: battery
    market_component: market
    max_import_price_ct_kwh: 15
    target_soc_percent: 80
    max_charge_power_w: 4000
    minimum_charge_power_w: 100
```

## Decision

Example:

```text
SOC                     40 %
target SOC              80 %
import price            10 ct/kWh
configured threshold    15 ct/kWh
device max charge     5000 W
site/strategy max      4000 W

→ battery.set_charge_power = 4000 W
```

Requested power is capped by both the configured strategy/site limit and the current battery-reported charge limit.

## Priority and reserve

`dynamic_battery_charge` is `OPTIMIZATION`.

`battery_reserve` is `SAFETY`.

Thus missing/stale SOC or reserve protection outranks economic battery behavior.

## What V0.1 intentionally does not claim

A current price below a fixed threshold does not prove it is the economically optimal charging hour.

Before production economic optimization, INS-EI must also consider:
- future import prices
- future export prices
- PV forecast
- consumption forecast
- battery efficiency/losses
- available/free battery energy
- reserve requirements
- expected later export value
- grid/connection limits
- battery cycling policy/cost where configured

Those belong to forecast-aware optimization, not the device plugin.

## Physical execution

The Strategy emits:

```text
battery.set_charge_power
```

A production battery plugin must explicitly declare and implement this command before Command Dispatcher will execute it.

Therefore the strategy can be evaluated safely in Shadow mode before Victron/Huawei write control is enabled.
