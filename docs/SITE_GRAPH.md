# SiteGraph — executable plant topology

## Purpose

`SiteGraph` turns the declarative Site YAML into a validated topology that Apps and Strategies can query.

It answers questions about **what the plant is**, for example:

- Which heat sources can heat this buffer?
- Which electrical source supplies this power-to-heat component?
- Which plugin instance provides a component?
- Which technical constraints apply to a component?
- Which components are connected by a known physical/logical relation?

It does **not** answer whether a device should run.

## Example

```text
                 ┌──────────────┐
                 │ pellet_boiler│
                 └──────┬───────┘
                        │ HEATS
                        ▼
┌──────┐ SUPPLIES ┌───────────────┐ HEATS ┌────────┐
│ grid │─────────▶│ power_to_heat │──────▶│ buffer │
└──────┘          └───────────────┘       └────────┘
```

The graph knows that both `pellet_boiler` and `power_to_heat` can heat `buffer`.

It does **not** choose between pellets and electricity. That belongs to Strategy.

## Validation

On construction the graph rejects:

- duplicate component IDs
- unknown component kinds
- components referencing unknown plugin instances
- relations with missing source/target components
- unknown relation types
- duplicate constraint IDs
- constraints targeting unknown components

A site with invalid topology must fail at configuration/startup rather than silently running with an ambiguous model.

## Initial relation vocabulary

- `HEATS`
- `CHARGES`
- `SUPPLIES`
- `MEASURES`
- `CONTROLS`
- `CONNECTED_TO`

Relations are directional when physical meaning has a direction.

## Queries

Examples:

```python
graph.sources("buffer", "HEATS")
graph.targets("grid", "SUPPLIES")
graph.constraints_for("buffer")
graph.component("pellet_boiler")
```

Apps and Strategies should query the graph rather than encode assumptions such as “the AC-THOR always heats the buffer”.

## Architecture boundary

**Plugin**  
Knows how a device communicates and what its vendor data means.

**SiteGraph**  
Knows which real components exist and how they are connected.

**Strategy**  
Knows what should happen and why.

This distinction is mandatory. SiteGraph must never contain tariff comparisons, optimization objectives, comfort decisions or customer-name branches.

## Future extensions

Only add these when required by real installations:

- ports/connection points for complex hydraulic topology
- multiple energy carriers
- flow direction/state
- heat-network nodes
- redundancy/priority metadata
- topology visualization
- graph consistency rules by component kind

The current graph intentionally stays small enough for residential systems while remaining extensible for future heating-plant use.
