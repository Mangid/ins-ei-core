# INS-EI Roadmap

## Phase 0 — Architecture contract
- [x] Green-field repository separated from INS-EI Pilot
- [x] Define platform / app / plugin / site separation
- [x] Home Assistant explicitly optional
- [x] Customer-specific logic must not leak into Core
- [ ] Define plugin manifest and lifecycle
- [ ] Define canonical point/capability model
- [ ] Define site model schema
- [ ] Define strategy interface
- [ ] Define configuration/version migration rules

**Exit criterion:** We can explain exactly where any new feature belongs before implementing it.

## Phase 1 — Standalone Core
Build the smallest useful INS-EI runtime: plugin discovery/install/enable/disable/update, instance configuration, common state/data bus, logging, health, diagnostics, telemetry, local API and safe restart/recovery.

**Exit criterion:** A clean Linux/Docker installation can run INS-EI and one plugin by itself, without Home Assistant.

## Phase 2 — First plugins
Initial targets: ÖkoFEN, my-PV, smart meter/SHR-DZM, Market, Forecast, Weather and optional Home Assistant bridge.

A plugin owns protocol/device communication, vendor-to-canonical translation, commands and its communication diagnostics. It does not own economic or cross-system strategy.

**Exit criterion:** Plugins can be installed and updated independently and expose standardized data/capabilities.

## Phase 3 — Site model
Represent GRID, PV, BATTERY, HEAT_GENERATOR, BUFFER, DHW, POWER_TO_HEAT, HEAT_METER, PUMP/VALVE, MARKET, FORECAST and WEATHER, including topology, limits and permitted actions.

**Exit criterion:** Two materially different customer plants can be represented without customer-specific Core code.

## Phase 4 — Apps and strategy
- **Heating:** monitoring, diagnostics and heating-specific service/control.
- **Energy:** PV/battery/grid/heat optimization, forecasts, dynamic tariffs and economic decisions.
- **Plant (later):** heating plants/networks, heat quantities, losses, generators, pumps, storage and larger batteries.

Strategies consume canonical plant state and constraints and never call vendor APIs directly.

## Phase 5 — Pilot migration
Selectively migrate proven Pilot functions: tariff logic, forecasts, battery optimization, thermal storage logic, decision explanations and remote telemetry/update concepts. Each component must first satisfy the new architecture boundaries.

## Phase 6 — Production operations
TEST/PROD separation, fleet overview, version inventory, health checks, remote update/rollback, alerting, audit trail, configuration backups and staged releases.

## Deliberately not now
- every possible vendor
- heating-plant optimizer immediately
- duplicating Home Assistant
- individual customer workflows in Core
- premature generalization of every future case
