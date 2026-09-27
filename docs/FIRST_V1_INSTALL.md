# First V1 Shadow Installation

The first real installation should run **parallel to INS-EI Pilot**.

## Purpose

Collect real canonical data and make the new architecture visible before handing it physical control.

Initial state:

```text
INS-EI Pilot → existing control remains active
INS-EI V1    → Learning / Shadow / Historian / visualization
```

## Start

1. Copy `config/site.home-v1-shadow.example.yaml` to `config/site.local.yaml`.
2. Fill local device addresses and ÖkoFEN password. Never commit credentials.
3. Start:

```bash
docker compose up -d --build
```

4. Open:

```text
http://<INS-EI-host>:8080/
```

## What should be visible

- Core health
- software Safety state
- plugin heartbeat
- automatically generated plant schematic
- live canonical values
- Learning Model count/status
- capability autonomy state
- persistent Historian under `./data`

## Control policy

The first V1 installation is Shadow-first. Unknown/unconfigured capabilities are default-deny at the Autonomy Gate.

Do not enable autonomous writes merely to test the UI.

## Missing for the full home model

The first template intentionally contains only currently implemented production-style plugins:
- ÖkoFEN
- my-PV read path
- SHRDZM

Victron/Pylontech/PV battery integration and Market/Forecast providers are the next required real adapters before the full Energy V1 can replace Pilot functionality.
