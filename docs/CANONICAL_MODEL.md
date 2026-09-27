# Canonical Model v0.1

The canonical model is the language between plugins, site model and apps.

## Component kinds

Initial vocabulary:

- `GRID`
- `PV`
- `BATTERY`
- `HEAT_GENERATOR`
- `BUFFER`
- `DHW`
- `POWER_TO_HEAT`
- `HEAT_METER`
- `ELECTRIC_METER`
- `PUMP`
- `VALVE`
- `MARKET`
- `FORECAST`
- `WEATHER`

The vocabulary is extensible, but additions require an architecture decision when they overlap an existing concept.

## Component identity

A component has a site-local stable ID independent of vendor and plugin.

Example:

```yaml
id: pellet_boiler
kind: HEAT_GENERATOR
provider:
  plugin_instance: oekofen_main
```

Changing from one vendor to another should not force strategy code changes if capabilities remain equivalent.

## Capabilities

Components advertise capabilities, e.g.:

```yaml
capabilities:
  read:
    - thermal.supply_temperature
    - thermal.return_temperature
    - state.operating_mode
  command:
    - heat.request
    - dhw.request_once
```

Strategies check capabilities instead of brands.

## Point envelope

Every observation contains:

```yaml
component_id: pellet_boiler
point: thermal.supply_temperature
value: 68.4
unit: °C
quality: GOOD
observed_at: 2026-09-27T10:00:00+02:00
source:
  plugin_instance: oekofen_main
```

Optional metadata may include raw source key and diagnostics, but apps must not depend on vendor raw keys.

## Initial semantic namespaces

- `power.*` — W/kW
- `energy.*` — Wh/kWh
- `thermal.*` — temperatures/thermal quantities
- `battery.*` — SOC, charge/discharge limits
- `state.*` — operating state/mode
- `flow.*` — volume/mass flow
- `market.*` — import/export prices
- `forecast.*` — future values
- `weather.*`
- `health.*`

Exact point registry will evolve from real plugins; names must describe physical meaning rather than vendor naming.

## Sign conventions

Canonical sign conventions must be explicit. Prefer directional points over overloaded signed values when ambiguity matters.

Example:
- `grid.import_power >= 0`
- `grid.export_power >= 0`
- `battery.charge_power >= 0`
- `battery.discharge_power >= 0`

Vendor-specific signed values are normalized by the plugin.

## Time series

Forecast and market data use timestamped slots:

```yaml
start: 2026-09-27T11:00:00+02:00
end: 2026-09-27T12:00:00+02:00
value: 0.2148
unit: EUR/kWh
quality: GOOD
```

Core preserves timezone-aware timestamps.
