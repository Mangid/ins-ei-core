# Data Freshness and Plugin Heartbeats

## Why

A value can be technically valid when received but unsafe for a current control decision minutes later.

Therefore INS-EI separates:

1. **point quality** — was the value valid when observed?
2. **point freshness** — is it still recent enough now?
3. **plugin heartbeat** — when did the source last complete a successful read?

## Automatic STALE

The State Store retains the original observation and derives `STALE` at read time.

Default V0.1 threshold:

```text
120 seconds
```

Per-point thresholds can override the default.

Example:

```python
state.set_stale_threshold("grid", "grid.export_power", 10)
```

A point received as `GOOD` becomes effectively `STALE` after its threshold. The stored source observation is not rewritten; freshness is derived from time.

Existing `INVALID` or `UNAVAILABLE` quality is preserved.

## Strategy behavior

`StrategyContext.good_value()` uses the freshness-aware State Store.

Therefore a strategy automatically receives no usable value when a required point is:
- missing
- INVALID
- UNAVAILABLE
- STALE

For example, `thermal_surplus_storage` will not start a new heating action based on an old grid-export measurement.

## API

`GET /state` includes for every point:
- observed timestamp
- effective quality
- current `age_seconds`
- `stale_after_seconds`

`GET /health` includes per plugin:
- lifecycle status
- last error
- last successful read timestamp
- age of last successful read

## Metrics

Per plugin:
- `plugin.<instance>.last_read_ok`
- `plugin.<instance>.points_last_read`
- `plugin.<instance>.last_read_age_seconds`

These are building blocks for fleet monitoring.

## Freshness is semantic

Not all points should use the same threshold.

Examples:
- grid power: seconds
- battery power/SOC: seconds to tens of seconds
- buffer temperature: tens of seconds/minutes
- daily energy counter: minutes
- market price slot: valid for its time interval
- forecast: valid according to forecast generation/slot metadata

The default is a safe baseline, not the final semantic policy.

## Next step

Move freshness requirements into the canonical point/capability definitions so plugins/apps can declare appropriate defaults, and let Site configuration override them when necessary.
