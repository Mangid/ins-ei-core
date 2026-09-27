# Plugin Contract v0.1

## Purpose

A plugin connects INS-EI to exactly one device family, protocol or external service responsibility. Plugins are independently installable and versioned.

Plugins **know devices/services, not plant strategy**.

## Package layout

```text
plugin/
├── manifest.yaml
├── plugin.py
├── schemas/
└── tests/
```

## Manifest

Minimum fields:

```yaml
api_version: ins-ei.plugin/v1
id: oekofen
name: ÖkoFEN
version: 0.1.0
kind: device
entrypoint: plugin:OekofenPlugin
capabilities:
  - heat_generator
  - dhw
permissions:
  network: true
  filesystem: false
```

`id` identifies the plugin package, not a customer or device instance.

One plugin may have multiple configured instances at a site.

## Lifecycle

```text
DISCOVERED
   ↓
INSTALLED
   ↓
CONFIGURED
   ↓
STARTING
   ↓
RUNNING ─────→ DEGRADED
   │              │
   ├──────────────┘
   ↓
STOPPING
   ↓
STOPPED

Any unrecoverable startup/runtime failure → FAILED
```

Required operations:

- `validate_config()`
- `start()`
- `stop()`
- `health()`
- `read_points()`
- `execute(command)` when write capabilities exist

Optional:
- `discover()`
- `diagnostics()`
- `migrate_config()`

## Plugin output

Plugins publish canonical points, not arbitrary HA-style entity identifiers.

Example:

```json
{
  "component_id": "pellet_boiler",
  "point": "supply_temperature",
  "value": 68.4,
  "unit": "°C",
  "quality": "GOOD",
  "observed_at": "2026-09-27T10:00:00+02:00"
}
```

Quality is mandatory:
- `GOOD`
- `STALE`
- `UNAVAILABLE`
- `INVALID`

## Commands

Strategies/apps issue canonical intents such as:

```text
heat_generator.request_heat
dhw.request_once
battery.set_charge_power
battery.set_discharge_power
power_to_heat.set_power
```

The responsible plugin translates the canonical command into the vendor protocol.

## Errors and diagnostics

A plugin owns:
- communication timeout/retry policy
- protocol/authentication errors
- vendor error decoding
- raw diagnostics needed for service
- rate limiting

Core owns lifecycle supervision and overall health.

## Hard boundary

Forbidden inside plugins:
- electricity-vs-pellet economic decisions
- PV/battery optimization
- customer-name branching
- cross-device orchestration

Those belong to Apps/Strategy/Site.
