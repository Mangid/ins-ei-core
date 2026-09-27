# Architecture

## Responsibility model

### Plugin — knows the device/service
Plugins know protocols, authentication, vendor semantics, polling, commands, communication errors and diagnostics. Examples include ÖkoFEN, my-PV, Victron, Huawei, Fronius, Hoval, Modbus, MQTT, market and forecast APIs.

A plugin must not decide whether electricity should be sold, a battery charged, or a pellet boiler started for economic reasons.

### Site instance — knows the plant
The site model describes installed components, topology, technical constraints and allowed operations: which buffer belongs to which generator, battery/grid/PV relationships, temperature/power/SOC limits, available heat paths and whether grid charge/export is permitted.

### INS-EI strategy — knows why and when to act
Strategy combines site state, constraints, prices, forecasts and objectives. It decides between PV use/export, battery charge/discharge, power-to-heat/pellets, DHW requirements and similar cross-system choices. It never depends on vendor entity IDs or protocols.

## Customer-specific behavior
Differences are represented in this order:
1. topology/site model
2. parameters and limits
3. reusable strategy modules
4. optional small Site Rules for true exceptions

Forbidden:
```python
if customer == "kaufmann":
    ...
```

Preferred:
```text
site capabilities + topology + parameters
        ↓
reusable strategy modules
        ↓
decision
        ↓
canonical command
        ↓
plugin
```

If the same special rule appears at a second site, it is a strong candidate to become a reusable strategy capability.

## Home Assistant
Home Assistant is an optional integration/bridge. INS-EI Core, site model, strategies and plugins must remain operational without HA. HA may expose or consume data, but an HA restart or entity change must not inherently stop core energy/heating operation.

## Apps on one platform
The platform owns runtime concerns. Domain apps own domain logic:
- **Heating** — service/monitoring/control around heating systems.
- **Energy** — cross-domain economic and energy optimization.
- **Plant** — later, larger heating plants/networks and industrial-style systems.

An installation activates only what it needs.

## Safety and explainability
Every control action should be attributable to current measured state, site constraints, strategy/rule, forecast/price inputs where applicable, and the resulting command/target plugin. Control must fail safely when required data is stale or unavailable.

## Architectural test for every change
1. Device/protocol knowledge? → Plugin.
2. Physical topology or site-specific limit? → Site model/config.
3. Reusable decision logic? → Strategy/App.
4. Truly unique behavior? → small Site Rule.
5. Runtime/infrastructure used by all? → Core.

If unclear, resolve responsibility before implementing.
