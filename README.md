# INS-EI

INS-EI is the new modular technical platform for INS energy, heating and plant applications.

This repository starts on a green field. The existing **INS-EI Pilot** remains a reference/prototype and is not the architectural foundation of this project.

## Four binding architecture rules

> **Plugins know devices.**  
> **The instance knows the plant.**  
> **INS-EI knows the strategy.**  
> **Home Assistant is optional — never a prerequisite.**

These rules are architectural guardrails. New code should be reviewed against them.

## Goal

INS-EI shall be usable at very different sites without turning the core into customer-specific code:

- simple ÖkoFEN monitoring/service without energy management
- residential energy management with PV, battery, heat and dynamic tariffs
- complex heating/energy plants such as heating networks and heating plants
- future applications not yet known today

The platform provides common infrastructure. Applications provide domain logic. Plugins provide integration with devices and external services.

## Target structure

```text
INS-EI Platform
├── Core
│   ├── runtime
│   ├── data/event model
│   ├── site model
│   ├── logging & diagnostics
│   ├── health/telemetry
│   └── update/plugin management
├── Apps
│   ├── Heating
│   ├── Energy
│   └── Plant          # later
├── Plugins
│   ├── devices
│   ├── market
│   ├── forecast
│   ├── weather
│   └── Home Assistant # optional
└── Site
    ├── plant configuration
    ├── strategy parameters
    └── optional custom rules
```

## V1 focus

1. stable standalone runtime without Home Assistant
2. plugin lifecycle and defined plugin API
3. standardized points/capabilities
4. site/plant model
5. health, logs and diagnostics
6. central update/plugin mechanism
7. first real plugins: ÖkoFEN, my-PV, smart meter
8. prove the architecture on two different real installations
9. only then migrate strategy/optimizer functions from Pilot

See [ROADMAP.md](ROADMAP.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DECISIONS.md](docs/DECISIONS.md).

## Pilot policy

Do not copy the Pilot wholesale. Existing Pilot components may be reused only after they have been adapted to the new interfaces and responsibilities. There must be no customer-name branches such as `if site == "kaufmann"` in Core or generic strategy code.
