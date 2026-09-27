# Strategy Engine v0.1

## Purpose

The Strategy Engine turns a known plant state into explainable canonical intents.

It sits above plugins and SiteGraph:

```text
Plugins → canonical state
              +
          SiteGraph
              ↓
       Strategy modules
              ↓
        Strategy Engine
              ↓
          Decision
              ↓
      canonical intents
              ↓
       command dispatcher
              ↓
           Plugins
```

The command dispatcher is intentionally the next layer; Strategy does not call plugins directly.

## Priority order

1. `SAFETY` — hard technical/safety protection
2. `MANDATORY` — required service/comfort such as DHW minimum
3. `SITE_RULE` — exceptional site-specific rule
4. `OPTIMIZATION` — economic/energy optimization
5. `FALLBACK` — HOLD

A lower-priority economic optimization can therefore never override a safety constraint or mandatory minimum requirement.

## Proposal

A module returns either no proposal or a proposal containing:

- strategy ID
- action
- priority
- human-readable reason
- confidence
- evidence
- zero or more canonical intents

Example:

```text
strategy: dhw_minimum
action: REQUEST_DHW_HEAT
priority: MANDATORY
reason: DHW 47.0 °C below configured minimum 50.0 °C
intent:
  target: pellet_boiler
  command: dhw.request_once
```

There is no `ww1.heat_once` in Strategy. That translation belongs to the ÖkoFEN plugin.

## First reusable module: dhw_minimum

The first module intentionally proves customer independence.

It is configured with:
- DHW component
- canonical temperature point
- minimum temperature
- selected heat-source component
- canonical command

Thus one site may satisfy minimum DHW using an ÖkoFEN one-time charge while another future site may use a different heat source/command without changing the rule's basic purpose.

## Explainability

Every Decision stores all considered proposals, not only the winner. This is required so INS-EI can later explain why an optimization did not run.

Example:

```text
Winner: dhw_minimum / MANDATORY
Reason: DHW below minimum

Considered:
- dhw_minimum: REQUEST_DHW_HEAT
- battery_export: EXPORT (lower priority)
- hold: HOLD
```

## Hard architecture rule

Strategies:
- may read canonical state
- may query SiteGraph
- may read site parameters/forecasts/market inputs
- may produce canonical intents

Strategies may **not**:
- call vendor APIs
- depend on Home Assistant entity IDs
- contain vendor register addresses
- branch on customer names

## Next steps

1. command dispatcher with capability validation
2. strategy module loading from Site configuration
3. technical constraint/safety strategy
4. thermal surplus storage
5. dynamic battery charging/export
6. decision history and API
