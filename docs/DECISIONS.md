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
