# Historian v0.1

## Purpose

Historian is the persistent memory required for:
- Outcome Tracking
- Learning Models
- model-quality measurement
- Value Accounting
- audit/explanation
- seasonal/operating-regime learning
- change-aware historical analysis

## Local storage

V0.1 uses SQLite on each INS-EI instance.

Default path:

```text
data/<site-id>/historian.sqlite3
```

SQLite is deliberately chosen for the edge runtime because it is transactional, robust, dependency-light and easy to back up/export. Central synchronization can be layered above the Historian contract later.

## Stored domains

### observations
Canonical measured points with:
- observation time
- recording time
- site/component/point
- value/unit/quality
- plugin instance
- context version

### decisions
- correlation ID
- winning Strategy/action
- priority/confidence/reason
- canonical intents
- all considered proposals/evidence
- context version

### commands
- same correlation ID
- target/command/parameters
- resolved plugin instance
- success/failure/blocked status
- result/error
- context version

### events
Generic correlated lifecycle/change/outcome events.

## Correlation

Every Strategy evaluation receives a unique correlation ID.

```text
observed plant state
       ↓
decision [correlation=A]
       ↓
intent
       ↓
command attempt [A]
       ↓
result [A]
       ↓
future outcome [A]
```

Endpoint:

```text
GET /history/trace/{correlation_id}
```

returns the stored decision, commands and correlated events.

## Context version

V0.1 already stores a `context_version` field so historical samples can be tied to the plant/tariff/model context under which they occurred.

The current runtime placeholder `site-v1` is temporary.

Next implementation replaces it with real:
- Site configuration version
- component lifecycle/version
- tariff version
- Learning Model versions

## Retention principle

Historical observations are not deleted merely because a component or tariff changes.

Instead, history retains the context/version that was valid at the time. Learning and Value Accounting decide which historical samples remain comparable/applicable.

## Next: Outcome Tracking

The next layer will attach expectations to a decision and later measure the actual result over a defined observation window.

Example:

```text
decision: charge buffer with 4 kW for 60 min
expected: upper buffer +7 K
actual:   upper buffer +5.8 K
residual: -1.2 K
```

Those residuals become training/evaluation data for Learning Models.
