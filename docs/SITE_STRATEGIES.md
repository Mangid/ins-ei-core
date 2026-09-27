# Site-configured strategies

INS-EI strategy behavior is selected by Site configuration, not customer-specific Python branches.

## Same module, different plant

A residential site may configure:

```yaml
- id: dhw_minimum
  config:
    dhw_component: dhw
    minimum_c: 50
    heat_source: pellet_boiler
    command: dhw.request_once
```

Another installation can use the same module with a different minimum or later a different compatible heat source.

The module implementation remains unchanged.

## Startup validation

When strategies are loaded, their referenced components are resolved through SiteGraph.

For `dhw_minimum` the configured heat source must actually have a `HEATS` relation to the configured DHW component. A typo or impossible plant path therefore fails during configuration rather than becoming a bad runtime decision.

## No customer identities

Example Site YAML files may model known plant types, but production strategy code must never branch on site/customer identity.

Correct:
```text
minimum_c = site strategy parameter
heat_source = component reference
```

Incorrect:
```python
if customer == "Kaufmann":
    minimum_c = 48
```

## Evaluation API

`POST /strategy/evaluate` evaluates current canonical state without executing physical commands.

It returns:
- winning action
- strategy
- priority
- confidence
- human-readable reason
- canonical intents
- all considered proposals/evidence

This endpoint is deliberately evaluation-only. Physical execution remains a separate controlled step through Command Dispatcher.
