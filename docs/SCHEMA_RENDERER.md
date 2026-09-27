# Automatic Schematic Rendering

INS-EI can now render a first schematic directly from the vendor-neutral Site View.

Endpoint:

```text
GET /site/schema.svg
```

## Data flow

```text
Site YAML
   ↓
SiteGraph
   +
StateStore
   ↓
Site View
   ↓
SVG renderer
   ↓
live plant schematic
```

The renderer has no ÖkoFEN, my-PV, Victron or Huawei knowledge.

## V0.1 layout

The first renderer uses deterministic semantic columns:

```text
sources → converters → storage → transport/control → consumers/networks
```

Examples:
- heat generators and PV/grid toward the source side
- power-to-heat as converter
- buffer/DHW/battery as storage
- pumps/mixers/valves as transport/control
- heating circuits/networks as consumers

Storage components render vertically and sensor positions map to their normalized physical position.

## Live data

The renderer can display current canonical points and positioned sensor values including quality.

The SVG is intentionally simple. Its purpose is to prove that the plant model is sufficient to generate a visualization automatically.

## Future renderer

A production GUI may replace SVG layout with an interactive graph editor/rendering library while preserving the same Site View contract.

Potential features:
- drag/drop layout with saved presentation coordinates
- animated flow when pump/energy flow is active
- temperature gradients on storage
- click component for details/diagnostics
- alarms and stale-data highlighting
- electrical and hydraulic layers
- zoom/pan
- edit mode for ports/connections/sensors

The renderer remains a view. SiteGraph/Site configuration remains the source of truth.
