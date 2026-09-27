# Site Model v0.1

A Site describes the physical installation and its constraints. It does not contain vendor protocol logic.

## Example skeleton

```yaml
api_version: ins-ei.site/v1
site:
  id: example-home
  timezone: Europe/Vienna

plugin_instances:
  - id: oekofen_main
    plugin: oekofen
    config_ref: secrets/oekofen_main

components:
  - id: pellet_boiler
    kind: HEAT_GENERATOR
    provider: oekofen_main
    capabilities:
      - heat.request
      - dhw.request_once

  - id: buffer
    kind: BUFFER
    properties:
      volume_l: 800
      max_temperature_c: 75

relations:
  - from: pellet_boiler
    to: buffer
    type: HEATS

constraints:
  - id: buffer_max_temp
    type: MAX_VALUE
    target: buffer.thermal.temperature
    value: 75
    unit: °C

apps:
  heating:
    enabled: true
  energy:
    enabled: false

strategy:
  modules: []

site_rules: []
```

## What belongs here

- installed components
- physical/electrical/hydraulic relationships
- capacities and technical limits
- enabled capabilities/actions
- site timezone
- enabled INS-EI apps
- references to plugin instances
- strategy parameters specific to this plant

## What does not belong here

- vendor API implementation
- secrets in plain text
- algorithm implementation
- customer-name conditionals

## Relations

Initial relation vocabulary:

- `HEATS`
- `CHARGES`
- `SUPPLIES`
- `MEASURES`
- `CONTROLS`
- `CONNECTED_TO`

Relations must be directional where direction has physical meaning.

## Three architecture tests

### A — Heating-only ÖkoFEN customer
May contain only HEAT_GENERATOR/DHW/BUFFER plus ÖkoFEN plugin and Heating app. No Energy app, PV, battery, market or HA required.

### B — Residential energy management
May combine GRID/PV/BATTERY/BUFFER/DHW/POWER_TO_HEAT/HEAT_GENERATOR with Market/Forecast/Weather and Energy strategies.

### C — Heating plant/network
May combine multiple HEAT_GENERATOR, BUFFER, HEAT_METER, ELECTRIC_METER, PUMP and VALVE components. Plant-specific algorithms can be added later without changing device plugin responsibilities.

If the model cannot represent all three without customer-specific Core code, the model is incomplete.
