# Learning Model Registry and Readiness

## Model Registry

Every learned model is explicitly registered with:
- stable model ID
- model version
- capability it supports
- lifecycle status
- dependencies
- metadata
- status reason/timestamp

Statuses:

```text
LEARNING
READY
DEGRADED
INVALIDATED
```

## Dependencies

Models declare what knowledge they depend on.

Example:

```text
buffer_thermal v3
depends on:
- component: buffer
- sensor: buffer_top
- sensor: buffer_middle
- topology: hydraulic-v12
```

If a dependency changes, only affected models are invalidated.

Example:

```text
battery replaced
→ battery_efficiency INVALIDATED
→ battery optimization readiness affected

building_heat remains unchanged
PV correction remains unchanged
```

## Learning Readiness

Readiness is evidence-based.

V0.1 assessment supports:
- minimum number of OBSERVED outcomes
- maximum fraction of UNOBSERVABLE outcomes
- maximum MAE
- maximum RMSE
- minimum number of context buckets

Context buckets represent coverage of meaningfully different conditions, for example:
- sunny / cloudy / poor PV
- warm / transition / cold
- low / medium / high load
- different SOC bands

A large sample count from only one operating condition is not automatically sufficient.

## READY is not AUTONOMOUS

This distinction is mandatory.

```text
Model status:
LEARNING → READY

Capability operation:
LEARNING → SHADOW → ASSISTED → AUTONOMOUS
```

A READY model means the evidence satisfies its readiness policy.

It does **not** grant physical control permission by itself.

Autonomy additionally requires:
- Safety requirements satisfied
- required canonical data healthy/fresh
- capability explicitly permitted
- physical plugin write capability proven/enabled
- Site constraints satisfied
- applicable model dependencies valid
- operator/site autonomy policy

## Regression

A model can move away from READY when:
- residuals worsen
- data becomes unobservable too often
- operating coverage changes
- dependency changes
- plant behavior drifts

Depending on cause it may become:
- LEARNING
- DEGRADED
- INVALIDATED

Capability autonomy can then independently fall back to SHADOW/ASSISTED.

## API

`GET /learning/models` exposes model versions, status, dependencies and reasons.

## Next implementation

Persist Model Registry state in Historian/database and connect Outcome Tracking evidence to automatic readiness reassessment.

Then introduce a separate Capability Autonomy Gate that consumes model readiness plus Safety/site/operator policy.
