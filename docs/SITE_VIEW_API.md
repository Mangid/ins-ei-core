# Site View API

## Principle

The future GUI must not reconstruct plant meaning from vendor plugins.

It receives a prepared vendor-neutral view built from:

```text
SiteGraph + StateStore → Site View API → GUI
```

Endpoint:

```text
GET /site/view
```

## Output

The view contains:
- components and kinds
- component properties
- provider references
- ports
- sensor positions
- current canonical sensor values
- all current canonical component points
- point quality and age
- hydraulic/electrical/data connections
- high-level relations
- technical constraints

## UI consequence

A renderer can choose a symbol by component kind:

```text
HEAT_GENERATOR → boiler/generator symbol
BUFFER         → vertical storage symbol
DHW            → DHW cylinder
POWER_TO_HEAT  → electric heater
PUMP           → pump
MIXER          → mixing valve
HEAT_METER     → meter
GRID/PV/BATTERY→ electrical symbols
```

It then places ports/connections and overlays live values.

No renderer should contain logic such as:

```text
if plugin == "oekofen": draw boiler
```

It should use:

```text
if kind == "HEAT_GENERATOR": draw heat generator
```

## Sensor rendering

For a buffer, normalized sensor positions can directly map to vertical screen position:

```text
0.0 top
│ ● 0.05
│   ● 0.25
│      ● 0.50
│          ● 0.75
1.0 bottom
```

The same model therefore supports both plant understanding and visualization.

## Editing direction

Later the GUI can work in reverse:

```text
add component
→ configure ports/properties
→ connect ports
→ position sensors
→ validate
→ save Site model
→ rebuild SiteGraph
```

The saved Site model remains the source of truth.

## Separation

The Site View is a read model. It does not:
- make strategy decisions
- call device APIs
- bypass Command Dispatcher
- change topology
- contain vendor semantics

Future topology editing will use a separate validated configuration API.
