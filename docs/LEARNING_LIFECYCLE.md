# Learning Lifecycle and Self-Optimizing Sites

## Vision

INS-EI is not commissioned by manually programming the optimal behavior of every customer installation.

A new site starts with:
- a validated physical SiteGraph
- installed capabilities
- hard technical constraints
- safety rules and emergency-stop behavior
- required comfort/service boundaries
- tariff/cost definitions
- explicitly permitted physical actions

Everything that can safely be learned from operation should increasingly be learned from the site's own historical data.

> **We define the boundaries. INS-EI learns how the real plant behaves inside those boundaries and continuously improves its operation.**

## Lifecycle

```text
COMMISSIONING
      ↓
LEARNING
      ↓
SHADOW_OPTIMIZATION
      ↓
ASSISTED
      ↓
AUTONOMOUS
      ↓
CONTINUOUS_LEARNING
```

### COMMISSIONING

Validate:
- topology
- sensors/actuators
- canonical data quality
- safety limits
- permitted commands
- tariffs/cost model
- basic fallback behavior

No learned model is trusted yet.

### LEARNING

INS-EI observes the real plant and builds historical models.

Examples:
- electrical load patterns
- PV forecast bias
- battery usable capacity and efficiency
- DHW demand patterns
- buffer charge/discharge behavior
- building heat demand
- thermal losses
- heating response to outdoor temperature
- boiler runtime/thermal yield
- heat-network losses

Optimization actions remain non-autonomous unless explicitly permitted by a safe deterministic rule.

### SHADOW_OPTIMIZATION

INS-EI calculates what it would do, but does not execute optimization commands.

Every proposal records:
- input state
- forecasts
- learned-model values
- intended action
- expected outcome

The actual plant evolution is then compared with the predicted outcome.

### ASSISTED

Selected capabilities may propose actions for operator approval or operate within deliberately narrow permissions.

### AUTONOMOUS

A capability may execute optimization decisions when its learning readiness, data quality, safety requirements and permissions satisfy configured release criteria.

### CONTINUOUS_LEARNING

Autonomous operation does not end learning.

Every decision becomes another learning sample:

```text
state + forecast
      ↓
decision/action
      ↓
expected outcome
      ↓
actual outcome
      ↓
error/residual
      ↓
model update
      ↓
future decision improves
```

## Capability-specific autonomy

Autonomy is not a single global switch.

Example:

```text
PV forecast correction       READY / AUTO
Battery efficiency model     READY / AUTO
Battery optimization         READY / AUTO
DHW demand model             READY / AUTO
Buffer thermal model         LEARNING / SHADOW
Building heat model          LEARNING
```

A site may therefore safely automate mature capabilities while other areas continue learning.

## Learning readiness

A model does not become trusted merely because a fixed number of days has passed.

Readiness may consider:
- number of valid observations
- time coverage
- operating-state coverage
- weather/temperature coverage
- forecast-error statistics
- model residual/error
- stability over time
- missing/stale-data rate
- whether relevant actions/outcomes have actually been observed

Example: three sunny days are not sufficient evidence for a robust PV correction model across poor-weather conditions.

## What must never be learned away

Learning may improve estimates and decisions, but it may not redefine hard boundaries such as:
- maximum safe temperatures
- minimum/maximum battery SOC limits defined as hard constraints
- maximum electrical/thermal power
- device/manufacturer safety constraints
- legal/protective requirements
- emergency-stop behavior
- operator-denied actions

Learned models are always subordinate to Safety and hard Site constraints.

## Regression / loss of confidence

Learning readiness is reversible.

If prediction error, data quality or plant behavior changes materially, a capability can automatically degrade:

```text
AUTONOMOUS → SHADOW
AUTONOMOUS → ASSISTED
READY → LEARNING
```

Examples:
- changed hydraulics
- replaced battery
- sensor moved/replaced
- building modification
- unusual consumption behavior
- persistent forecast/model error

INS-EI must prefer reduced autonomy over confident operation with an invalid model.

## Historian requirements

The Historian must preserve enough context to reconstruct learning samples:

- canonical observations and quality
- market and forecast slots
- weather
- Site/model version
- Strategy proposals and winning decision
- physical commands attempted/executed
- safety blocks
- expected outcome
- observed outcome
- model prediction/error
- model/version used
- learning readiness/confidence state

This allows both learning and later explanation/audit.

## Architectural separation

```text
Plugins            device facts
SiteGraph          physical plant
Historian          what happened
Learning Models    how this plant behaves
Strategy           what should be done
Optimizer          best plan within constraints
Safety             what may never be violated
```

Learning Models inform Strategy/Optimizer. They do not directly operate devices.

## Initial implementation order

1. Historian
2. decision/action correlation IDs
3. Outcome Tracking
4. model registry and model versions
5. learning-readiness framework
6. simple statistical models first
7. Shadow evaluation against actual outcomes
8. capability-specific autonomy gates
9. only then more advanced learning methods where they materially improve results

Complex ML is not a prerequisite. Reliable historical data and measurable prediction error come first.
