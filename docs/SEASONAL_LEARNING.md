# Operating Regime and Seasonal Learning

## Principle

INS-EI does not treat calendar seasons as the primary control model.

```text
December != automatically winter operation
September != automatically transition operation
```

Instead, each site learns its actual operating regimes from historical behavior and current/forecast conditions.

## Example regimes

Initial semantic labels may include:
- `SUMMER`
- `TRANSITION_WARM`
- `TRANSITION_COLD`
- `HEATING`
- `COLD_SPELL`

These are operating regimes, not calendar seasons.

A model may express uncertainty/probability rather than a hard switch:

```text
HEATING          72 %
TRANSITION_COLD  24 %
TRANSITION_WARM   4 %
```

## Inputs

Depending on available site capabilities:
- current outdoor temperature
- rolling outdoor-temperature means
- weather forecast
- heating-circuit activity
- measured/estimated heat demand
- buffer behavior
- indoor temperatures when available
- solar/PV conditions
- solar gains proxies
- day length / solar position
- DHW demand patterns
- historical operating outcomes

## Learned heating boundary

A site may learn the outdoor/rolling-temperature conditions at which meaningful space-heating demand begins.

The learned threshold may differ between spring and autumn due to:
- stored building heat
- solar gains
- occupancy/internal gains
- thermal inertia

This learned behavior informs optimization but does not override frost protection or other hard constraints.

## Three horizons

```text
Weather Forecast
hours / days
       ↓
Operating Regime
current thermal mode
       ↓
Seasonal Model
long-term learned site behavior
       ↓
Strategy / Optimizer
```

A site can therefore be in a transition regime while anticipating a short cold spell.

## Learning across years

The first heating/cooling year establishes evidence across weather conditions. Later years reuse prior knowledge while continuing to adapt.

Models are versioned and may lose readiness when:
- building fabric changes
- heating system/topology changes
- sensors move
- occupancy/load patterns change materially
- prediction residuals increase

## Safety boundary

Operating-regime learning may alter forecasts, priorities and optimization assumptions.

It may not redefine:
- frost protection
- maximum temperatures
- mandatory DHW minima
- hard battery limits
- hardware/manufacturer protection
- emergency-stop behavior
