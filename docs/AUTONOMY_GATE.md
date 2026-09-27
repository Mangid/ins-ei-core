# Capability Autonomy Gate

## Purpose

INS-EI separates three questions:

1. **What would be a good action?** → Strategy/Optimizer
2. **Is the action safe?** → Safety
3. **May INS-EI execute this capability autonomously?** → Autonomy Gate

A correct decision is not automatically an authorized physical action.

## Modes

Every capability can independently be:

```text
LEARNING
SHADOW
ASSISTED
AUTONOMOUS
```

### LEARNING
Models/data are still being established. No autonomous physical execution.

### SHADOW
INS-EI evaluates and records what it would do. No autonomous physical execution.

### ASSISTED
INS-EI may propose an action for operator approval. V0.1 still blocks automatic dispatcher execution.

### AUTONOMOUS
Automatic execution is possible only when all additional gates pass.

## AUTONOMOUS requirements

V0.1 Autonomy Gate requires:
- capability mode is AUTONOMOUS
- physical writes explicitly permitted
- every configured required Learning Model is READY

Other existing layers additionally require:
- software emergency stop inactive
- target component/provider valid
- plugin manifest declares command
- plugin executes command successfully
- Strategy/Site constraints have produced the intent

## Default deny

An unknown/unconfigured capability defaults to:

```text
LEARNING
physical_write_allowed = false
```

Therefore adding a new Strategy or plugin command cannot accidentally enable autonomous physical control.

## Command capability mapping

Initial mappings:
- `battery.*` → `battery_optimization`
- `power_to_heat.*` → `thermal_optimization`
- `dhw.*` → `dhw_control`
- `heat_generator.*` → `heating_control`

This mapping will later move into explicit command/capability metadata rather than remain prefix-based.

## Model regression

If a required model loses validity/readiness, the related capability can be degraded from:

```text
AUTONOMOUS → SHADOW
```

without disabling unrelated capabilities.

Example:

```text
battery replaced
→ battery model invalidated
→ battery_optimization SHADOW

dhw_control remains AUTONOMOUS
heating_control remains AUTONOMOUS
```

## Execution gates

Current normal physical path:

```text
Decision / Intent
      ↓
Command Dispatcher
      ↓
Safety Gate
      ↓
Autonomy Gate
      ↓
target/provider resolution
      ↓
plugin manifest command permission
      ↓
plugin execute
      ↓
Historian + Audit + Metrics
```

## API

`GET /autonomy` exposes configured capability modes and current assessment.

Future configuration/edit endpoints must themselves be authenticated/audited management operations.

## Important

READY is evidence about a model.

AUTONOMOUS is permission to act.

They are intentionally different concepts.
