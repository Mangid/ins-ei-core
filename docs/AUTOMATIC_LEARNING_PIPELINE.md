# Automatic Learning Pipeline

## Closed loop

INS-EI now connects the previously separate learning components:

```text
Outcome Tracking
      ↓
persist model evidence
      ↓
Learning Coordinator
      ↓
Readiness Policy
      ↓
Model Registry status
      ↓
Capability Autonomy Gate
```

## Persistence

Learning Model records and Outcome Evidence are stored in the local Historian SQLite database.

A restart therefore does not reset:
- model version
- model status
- dependencies
- readiness policy
- accumulated outcome evidence

## Automatic promotion

When persisted evidence satisfies the configured Readiness Policy:

```text
LEARNING → READY
```

The policy can include:
- minimum observed outcomes
- maximum unobservable fraction
- maximum MAE
- maximum RMSE
- minimum context-bucket coverage

## Automatic degradation

A model that was READY can become DEGRADED when newly accumulated evidence no longer satisfies its policy.

When that happens:

```text
Model READY → DEGRADED
Dependent Capability AUTONOMOUS → SHADOW
```

This is automatic and capability-specific.

## Invalidated models

A model explicitly INVALIDATED by a component/topology/sensor dependency change is not automatically promoted by ordinary readiness reassessment. It requires an explicit new/revalidated model lifecycle.

## Evidence integrity

Only Outcome Tracking results tied to a model ID/version enter that model's evidence set.

UNOBSERVABLE outcomes are stored as evidence about data/observation quality but carry no fabricated residual.

## Important limitation

V0.1 readiness uses the accumulated evidence set. Production evolution should support rolling evaluation windows and drift detection so very old good samples cannot hide recent deterioration.

## Next steps

- rolling readiness windows / drift detection
- persist capability autonomy configuration
- Site/component/tariff version objects and dependency invalidation events
- automatic context-bucket assignment
- first real learned model (buffer thermal behavior)
