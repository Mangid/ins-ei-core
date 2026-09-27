# Canonical Point Registry

## Purpose

The Point Registry defines the stable semantic language used between device plugins, StateStore, SiteGraph-aware Apps and Strategies.

A canonical point definition includes:

- semantic name
- canonical unit
- basic value type
- default freshness threshold
- description

Example:

```text
grid.export_power
unit: W
type: number
freshness: 10 s
meaning: active grid export, always non-negative
```

## Why it is strict

Without a registry, two plugins could expose:

```text
grid.power = -2400
net_power = 2400
einspeisung = 2.4 kW
```

and every strategy would need vendor/site-specific interpretation.

Instead, plugins normalize into one meaning:

```text
grid.import_power = 0 W
grid.export_power = 2400 W
```

StateStore rejects unknown canonical point names, incompatible units and basic type mismatches.

Vendor-specific values that do not yet have canonical semantics belong in plugin diagnostics/unmapped data until deliberately promoted.

## Freshness classes in V0.1

Initial defaults are based on control semantics, not vendor polling intervals:

- grid import/export power: 10 s
- active electrical/power-to-heat power: 15 s
- electrical voltage/current: 30 s
- burner/pump states: 60 s
- supply temperature: 120 s
- storage/general thermal temperature: 180 s
- configured temperature targets: 300 s
- outdoor temperature: 600 s
- cumulative energy totals: 300 s

These defaults are intentionally conservative and will be refined with real operating data.

Site-specific overrides remain possible.

## Evolution rule

Do not add a canonical point merely because a vendor exposes a field.

Promote a value into the registry when:
1. its physical/semantic meaning is understood,
2. its unit/sign convention is defined,
3. at least one App/Strategy/diagnostic use benefits from it,
4. the name can remain vendor-independent.

This keeps the canonical language small and stable.

## Current plugin check

The existing ÖkoFEN, my-PV, SHRDZM and demo plugin canonical outputs are represented in the registry. Unmapped vendor values remain diagnostic data.

## Future registry domains

Add only when implementation requires them:
- battery SOC/power/limits
- PV generation
- heat quantity/thermal power/flow
- market price slots
- forecast slots
- weather forecast
- alarms/faults
- fuel consumption
