# Value Accounting and Savings Model

## Goal

INS-EI should quantify the value it creates without presenting model assumptions as measured facts.

The central comparison is:

```text
actual operation with INS-EI
            vs.
counterfactual baseline without the optimization action
```

## Value categories

Potential contributions include:
- avoided grid import
- battery price arbitrage
- increased PV self-consumption
- improved PV export revenue
- power-to-heat versus alternative heat generation
- avoided pellet consumption
- avoided/shifted peak power where economically relevant
- later: reduced heating-network losses and plant operating costs

Contributions must not be naively summed when they overlap. Value Accounting owns attribution and prevents double counting.

## Evidence classes

Every reported value carries an evidence/confidence classification.

Examples:
- directly measured: imported/exported kWh and known tariff
- strongly derived: battery action with measured before/after energy and known prices
- modelled: avoided pellet consumption inferred from learned thermal efficiency
- uncertain: counterfactual requiring weak or incomplete baseline evidence

Reports may separate measured/strongly supported value from modelled value.

## Decision-level accounting

Historian correlation allows individual decisions to be evaluated:

```text
decision
→ action
→ measured outcome
→ counterfactual baseline
→ attributable value
→ confidence
```

Example:
- battery charged during low-price slot
- later energy displaced higher-price import
- account for learned round-trip efficiency
- calculate attributable monetary benefit

## Baseline versions

A baseline is versioned and time-bound.

Historical savings must use the tariff, plant configuration and model versions valid at the time of the event. A new tariff must not retroactively change historical savings.

## Change awareness

Component replacement, topology changes, tariff changes and model invalidation can change the valid baseline.

Historical data is retained, but the applicable context/version is preserved.

## Outputs

Possible cumulative KPIs:
- EUR saved
- kWh grid import avoided
- kWh PV additionally self-consumed
- kWh/kilograms alternative fuel avoided
- export revenue gained
- optional emissions indicators
- confidence/model-quality indicators

## Principle

INS-EI must be able to explain both **what it did** and **what measurable/modelled value that action created**.
