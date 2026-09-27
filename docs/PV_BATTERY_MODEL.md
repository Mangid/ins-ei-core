# PV and Battery Canonical Model

## Directional semantics

INS-EI does not expose vendor-specific signed battery power to Strategies.

```text
battery.charge_power     >= 0 W
battery.discharge_power  >= 0 W
```

Likewise PV generation is:

```text
pv.generation_power >= 0 W
```

A Victron, Huawei or other plugin is responsible for translating its native sign convention.

## Initial battery points

- `battery.soc`
- `battery.charge_power`
- `battery.discharge_power`
- `battery.max_charge_power`
- `battery.max_discharge_power`
- `battery.capacity_usable`
- `battery.energy_available`
- `battery.energy_free`

These are enough to begin generic reserve, charging and export strategies without binding them to a manufacturer.

## Battery reserve

The first generic battery module is `battery_reserve`.

It has SAFETY priority and blocks discharge optimization when:
- SOC is at/below configured reserve
- SOC is missing/stale

It intentionally produces no vendor command itself. It establishes a high-priority decision/constraint that later battery optimization must respect.

## Reference plugin

`energy-reference` is a contract-test plugin only. It proves the canonical PV/BATTERY interface before real Victron/Huawei providers are added.

Production device plugins will replace the reference source without changing Strategy semantics.

## Next strategy sequence

1. battery reserve / SOC protection
2. dynamic grid charging when economically useful
3. PV charging allocation
4. load support / avoided import
5. export/sell battery energy at attractive prices
6. forecast-aware multi-slot optimization

Economic strategies remain below SAFETY/MANDATORY priority.
