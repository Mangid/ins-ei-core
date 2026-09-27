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
