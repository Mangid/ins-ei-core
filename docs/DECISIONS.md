# Architecture Decisions

## ADR-001 — Green-field INS-EI
**Accepted — 2026-09-27.** INS-EI Pilot remains a working prototype/reference. The new platform is separate; Pilot code is migrated selectively rather than copied wholesale.

## ADR-002 — Device plugins are independent of strategy
**Accepted — 2026-09-27.** Plugins handle devices/services and expose canonical capabilities. Economic and cross-device decisions belong to INS-EI strategies/apps.

## ADR-003 — Site model owns plant-specific structure
**Accepted — 2026-09-27.** Customer hydraulics/electrical topology and technical limits belong in the site model/configuration, not customer-name branches in Core.

## ADR-004 — Home Assistant is optional
**Accepted — 2026-09-27.** INS-EI must run standalone. HA is an optional bridge/plugin and never a prerequisite for core operation.

## ADR-005 — One platform, multiple applications
**Accepted — 2026-09-27.** The common platform can support Heating, Energy and later Plant use cases. A site may use only heating monitoring, residential energy management, or a future heating-plant application.

## ADR-006 — Encapsulate customer complexity
**Accepted — 2026-09-27.** Customer behavior should primarily be expressed through topology, parameters and reusable strategies. Truly unique rules are isolated as small Site Rules; repeated Site Rules should become reusable capabilities.


## ADR-007 — SiteGraph is topology, not strategy
**Accepted — 2026-09-27.** INS-EI builds a validated SiteGraph from the site configuration at startup. The graph owns component identity, provider binding, physical/logical relations and technical constraints. It may be queried by Apps and Strategies, but it must not make economic, comfort or optimization decisions. This preserves the rule: the instance knows the plant; INS-EI Strategy knows what to do with it.

## ADR-008 — Canonical directional grid flows
**Accepted — 2026-09-27.** Vendor-specific signed grid power is normalized inside the meter plugin. Core and Strategy use separate non-negative `grid.import_power` and `grid.export_power` points. Vendor sign conventions remain diagnostics only.

## ADR-009 — Plugins are discovered, not registered in Core
**Accepted — 2026-09-27.** The Core discovers installed plugin manifests and dynamically loads declared entrypoints. Adding a device vendor must not require changing a static manufacturer registry in Core.


## ADR-010 — Strategies produce intents; dispatcher executes commands
**Accepted — 2026-09-27.** Strategy modules never call plugins directly. They produce canonical intents. A separate Command Dispatcher resolves the target component through SiteGraph, resolves its provider/plugin instance, verifies that the plugin manifest explicitly declares the command, and only then invokes the plugin. This creates a mandatory validation boundary between decision logic and physical writes.


## ADR-011 — Strategy behavior is configured by Site, not customer identity
**Accepted — 2026-09-27.** Reusable Strategy modules are instantiated from the Site configuration and validated against SiteGraph. Site-specific thresholds, selected components and permitted canonical commands are parameters. Customer/site names must never select algorithm branches in reusable Strategy code.


## ADR-012 — No physical control without central Safety Gate
**Accepted — 2026-09-27.** Every normal physical command must pass through the Command Dispatcher and central SafetyController immediately before plugin execution. An active INS-EI software emergency stop blocks normal outgoing commands regardless of their origin. This software interlock complements and never replaces required hardware safety systems.

## ADR-013 — Decisions and writes are auditable and observable
**Accepted — 2026-09-27.** Strategy decisions, physical command attempts/results, safety-state changes and important plugin lifecycle failures are first-class audit events. Runtime metrics are part of the Core architecture, not optional application diagnostics.


## ADR-014 — Optimization may propose capabilities that remain physically disabled
**Accepted — 2026-09-27.** Strategy evaluation and physical execution are separate. A Strategy may produce a canonical intent for a capability understood by the plant model even when the current device plugin has not yet enabled a proven write implementation. Command Dispatcher/manifest validation must block such execution. This allows safe Shadow-mode development without weakening the physical write boundary.


## ADR-015 — Data validity and freshness are separate
**Accepted — 2026-09-27.** Canonical observations retain source quality and observation time. StateStore derives effective STALE state when a GOOD observation exceeds its configured freshness threshold. Strategies consume freshness-aware state and must not treat an old GOOD observation as current. Plugin heartbeat is tracked separately from individual point freshness.


## ADR-016 — Canonical points require registry semantics
**Accepted — 2026-09-27.** A value becomes a canonical INS-EI point only after its vendor-independent meaning, unit/sign convention, value type and default freshness are defined in the Point Registry. StateStore validates canonical observations against this registry. Vendor fields without defined semantics remain plugin diagnostics/unmapped data rather than silently expanding the Core data model.


## ADR-017 — Dynamic battery charging starts rule-based, then becomes forecast-aware
**Accepted — 2026-09-27.** The first dynamic grid-charge strategy uses explicit current-price, SOC and charge-limit thresholds for transparent Shadow-mode behavior. It must not be described as globally economically optimal. Forecast-aware multi-slot optimization will later incorporate future tariffs, PV/consumption forecasts, efficiency, reserve and export opportunity cost without moving economic logic into battery plugins.
