# INS-EI Bus v1

Status: Accepted draft for implementation (2026-09-29)

## Principle

MQTT/TLS is the primary runtime communication bus between an INS-EI Core site and the central service platform.
The local Core remains fully operable without the central service. MQTT is transport, never control strategy.

Base topic:

    ins-ei/<site_id>/

## Topics

Retained:
- status                 online/offline, core version, boot/session id
- health                 current plugin/core health
- state                  compact canonical current-state snapshot
- learning               current Learning Summary
- forecast/pv            latest PV forecast supplied by central service
- forecast/consumption   latest consumption forecast supplied by central service
- update/status          current update-agent state

Non-retained/event:
- event                  site/operator/system events
- decision               strategy/shadow decisions
- command                centrally requested supervised/authorized command
- command/result         acknowledgement/result correlated by correlation_id

## Envelope

Every payload uses:

    {
      "api_version": "ins-ei.bus/v1",
      "site_id": "test-lab",
      "type": "learning.snapshot",
      "generated_at": "2026-09-29T03:00:00+02:00",
      "sequence": 123,
      "payload": {}
    }

Optional fields:
- correlation_id
- context_version
- core_version
- session_id

## Data rules

- Canonical INS-EI component/point names cross the bus; vendor-native names do not.
- Quality and observed_at travel with telemetry where relevant.
- Secrets, plugin passwords and credentials never travel over the bus.
- Core must tolerate broker/server outage and continue local operation.
- Forecasts carry generated_at, valid horizon and quality/expiry metadata.
- Commands require correlation IDs and explicit result messages.
- Physical command execution remains governed locally by Safety/Autonomy/Supervised policy.

## Cadence

- status: on connect/change, retained, MQTT LWT publishes offline.
- health: on meaningful change and periodic heartbeat.
- state: delta/event driven plus periodic compact snapshot.
- learning: on fit/change plus periodic 15-60 minute snapshot.
- event/decision/command/result: immediately, non-retained.
- forecasts: on central forecast generation/update, retained.

## Learning Summary

The Learning Summary is a stable diagnostic projection, not raw model storage.
It contains:
- historian duration, samples, signals
- commissioning provenance
- model id/version/status/phase/last_fit/reason
- model-specific diagnostic summaries
- evidence gaps / waiting contexts

Raw historian.sqlite3 and internal model persistence remain local.
