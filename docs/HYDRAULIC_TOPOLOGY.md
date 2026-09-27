# Hydraulic Topology Model

## Goal

INS-EI can represent a hydraulic schematic as machine-readable plant topology. The visual schematic is a future rendering of this model, not the source of truth.

## Two levels

### Component-level relation

Simple installations can continue to use:

```yaml
relations:
  - {from: pellet_boiler, to: buffer, type: HEATS}
```

This is sufficient when exact hydraulic connection points do not matter.

### Port-level connection

Detailed installations use ports:

```yaml
components:
  - id: pellet_boiler
    kind: HEAT_GENERATOR
    ports:
      - {id: supply, type: HYDRAULIC_SUPPLY}
      - {id: return, type: HYDRAULIC_RETURN}

  - id: buffer
    kind: BUFFER
    ports:
      - {id: top, type: HYDRAULIC}
      - {id: middle, type: HYDRAULIC}
      - {id: bottom, type: HYDRAULIC}

connections:
  - {from: pellet_boiler.supply, to: buffer.middle, medium: WATER}
  - {from: buffer.bottom, to: pellet_boiler.return, medium: WATER}
```

This preserves where energy enters/leaves the storage.

## Sensor positions

Storage sensors can be positioned on a normalized vertical axis:

```text
0.0 = top
1.0 = bottom
```

Example:

```yaml
sensors:
  - {id: top, position: 0.05}
  - {id: tpo, position: 0.25}
  - {id: middle, position: 0.50}
  - {id: tpm, position: 0.75}
```

The normalized model works independently of physical tank height.

## Kaufmann-style reference

The repository contains `config/site.kaufmann-hydraulic-reference.yaml` demonstrating:
- pellet boiler supply to buffer middle, return from bottom
- wood boiler supply to top, return from bottom
- electric stratified charging supply to top, return from bottom
- 600 L buffer
- four sensor positions
- separate DHW and heating-circuit components

It is a topology reference, not customer-specific Strategy code.

## Initial port types

- `HYDRAULIC`
- `HYDRAULIC_SUPPLY`
- `HYDRAULIC_RETURN`
- `ELECTRICAL`
- `DATA`

## Additional component kinds

The topology now allows:
- `MIXER`
- `HYDRAULIC_NODE`
- `HEAT_NETWORK`

alongside existing generators, buffers, DHW, pumps, valves, heat meters and heating circuits.

## What this model knows

- physical components
- ports
- connection endpoints
- nominal connection direction
- medium
- sensor location
- component properties
- high-level energy relations

## What it does not yet simulate

V0.1 does not calculate:
- pressure drop
- pump curves
- hydraulic balancing
- dynamic mass flow
- stratification physics
- mixing temperature
- pipe heat loss
- transient thermodynamics

Those may be added as specialized models later if useful. They are not required for the Core to understand topology.

## GUI direction

A future editor can render this model as a schematic:

```text
palette → components → ports → drag connections → sensors
                         ↓
                     Site YAML
                         ↓
                     SiteGraph
```

The same data then serves documentation, validation, visualization and Strategy/Optimizer topology queries.

## Compatibility

Port-level topology is optional. Existing simple Sites using only component-level relations remain valid.
