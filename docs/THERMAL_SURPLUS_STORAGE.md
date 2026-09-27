# Thermal Surplus Storage Strategy

## Goal

Use otherwise exported electrical surplus for thermal storage when the configured storage still has thermal capacity.

This is the first cross-sector INS-EI optimization module:

```text
GRID export
    ↓
electrical surplus
    ↓
POWER_TO_HEAT
    ↓
thermal storage
```

## Inputs

All inputs are canonical:

- `grid.export_power`
- configured storage temperature point
- SiteGraph topology
- configured maximum storage temperature
- configured power-to-heat maximum
- export reserve/deadband

No vendor registers or Home Assistant entities are used.

## Decision

Example:

```text
grid.export_power       3500 W
reserve_export_w         100 W
usable surplus          3400 W
buffer upper temp       55.0 °C
buffer max              75.0 °C
P2H max                 9000 W

→ request power_to_heat.set_power = 3400 W
```

The strategy is `OPTIMIZATION` priority. Mandatory DHW or future safety proposals therefore outrank it.

## Data quality / fail-safe

The module creates no new heating action if required grid export or storage-temperature data is absent or not `GOOD`.

It also produces no action when:
- storage is at/above configured maximum
- usable surplus is below minimum power
- no surplus remains after configured export reserve

## Topology validation

At configuration time INS-EI requires:

```text
GRID --SUPPLIES--> POWER_TO_HEAT --HEATS--> STORAGE
```

This prevents applying a generic strategy to a physically impossible path.

## Current execution status

The strategy can currently evaluate in Shadow mode and produce the canonical intent:

```text
power_to_heat.set_power
```

The current my-PV plugin intentionally does **not** declare/execute this command yet because the write interface has not been proven in the new plugin. Therefore the Command Dispatcher blocks physical execution.

This is intentional architecture behavior: a Strategy may understand what should happen while a device plugin still refuses an unproven write capability.

## Next evolution

Before closed-loop activation:
1. prove my-PV local power command/write interface
2. add command range validation in plugin manifest/config
3. add stale-age thresholds, not only quality state
4. add ramp/deadband behavior
5. decide interaction with battery charging and export price
6. add thermal forecast and economic comparison

The last two belong to higher-level Energy strategy/optimization, not the my-PV plugin.
