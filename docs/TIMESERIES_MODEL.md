# Market and Forecast Time-Series Model

## Why a separate store

Current physical state and future/planned data have different semantics.

```text
StateStore
- current measured observations
- point freshness
- device/source quality

TimeSeriesStore
- timestamped market/forecast slots
- explicit start/end
- generated-at timestamp
- source and metadata
```

Forecasts are therefore not faked as hundreds of current-state points.

## Canonical series V0.1

- `market.import_price` — ct/kWh
- `market.export_price` — ct/kWh
- `forecast.pv_energy` — kWh per slot
- `forecast.consumption_energy` — kWh per slot

## Slot model

Every slot contains:

```text
series
start
end
value
unit
quality
generated_at
source
metadata
```

Times must be timezone-aware.

Slots in the same series may not overlap.

## No hourly assumption

INS-EI must never assume that a market/forecast slot is one hour.

The explicit `start` and `end` allow:
- 15-minute prices
- 60-minute prices
- mixed future market products if needed
- forecast providers with different resolutions

Algorithms calculate duration from the slot itself.

## Strategy access

StrategyContext provides:
- current slot
- future GOOD slots over a requested horizon

This enables strategies and later the optimizer to combine future prices, PV and consumption on a common timeline.

## API

`GET /timeseries` exposes loaded canonical series and slot metadata.

## Provider responsibility

Market/Forecast plugins are responsible for:
- provider/API communication
- timezone normalization
- tariff/provider raw-field interpretation
- converting values into canonical series units
- reporting generation/source metadata

They do not decide when to charge a battery or heat a buffer.

## Next step: aligned planning horizon

The optimizer needs a timeline builder that takes series with potentially different slot boundaries and creates one common planning horizon without losing energy/price semantics.

Example:

```text
market:      60 min slots
PV forecast: 15 min slots
consumption: 30 min slots

          ↓ timeline alignment

optimizer: canonical planning intervals
```

That is the next prerequisite before rebuilding the Pilot's 24/48-hour optimization.
