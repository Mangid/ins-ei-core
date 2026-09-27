# Strategy Contract v0.1

Strategies are reusable decision modules inside an App.

They consume canonical state + site topology/constraints + optional forecasts/prices and produce **intents**, never vendor commands.

## Input

```text
StrategyContext
├── now
├── site_model
├── current_state
├── data_quality
├── forecasts
├── market
└── active_constraints
```

A strategy declares required and optional capabilities before execution.

## Output

```yaml
decision:
  strategy: dhw_minimum
  action: REQUEST_DHW_HEAT
  target: dhw
  confidence: HIGH
  reason: "DHW temperature below configured minimum"
  intents:
    - target: pellet_boiler
      command: dhw.request_once
      parameters: {}
```

Every decision must be explainable.

## Strategy categories

Examples, not hard-coded customer logic:

- `dhw_minimum`
- `thermal_surplus_storage`
- `pellet_backup`
- `dynamic_battery_charge`
- `battery_support_load`
- `battery_export`
- `pv_surplus_allocation`

A site activates and parametrizes modules.

## Precedence

Safety and hard technical constraints always override optimization.

Proposed order:
1. safety/technical constraints
2. mandatory service/comfort requirements
3. site rules
4. optimization strategies
5. fallback/hold

Conflicts must be resolved centrally and logged; plugins do not arbitrate strategy conflicts.

## Site Rules

Site Rules are a controlled escape hatch for genuinely unique plant behavior.

They:
- consume canonical data
- produce canonical constraints/intents
- cannot call vendor APIs directly
- must be separately named/versioned
- should be promoted into reusable strategy modules if repeated elsewhere

## Explainability

For every resulting action INS-EI should be able to answer:
- What state triggered it?
- Which constraint/strategy decided it?
- Which alternatives were rejected and why, when relevant?
- Which canonical intent was produced?
- Which plugin executed it?
