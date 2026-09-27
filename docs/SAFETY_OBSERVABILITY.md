# Safety, Audit and Metrics

## Safety principle

No physical INS-EI command may bypass the central `SafetyController`.

The Command Dispatcher checks the software emergency-stop state immediately before resolving/executing a physical command.

```text
Strategy / API / future operator command
              ↓
        canonical intent
              ↓
       Command Dispatcher
              ↓
          SAFETY GATE
         ↙           ↘
     blocked        allowed
                       ↓
                    plugin
                       ↓
                    device
```

## Software emergency stop

Endpoints:

- `GET /safety`
- `POST /safety/emergency-stop?reason=...`
- `POST /safety/reset?reason=...`

When active, outgoing physical commands through the dispatcher are rejected with `EMERGENCY_STOP_ACTIVE` and audited.

**Important:** This is an INS-EI software command interlock. It does not replace legally/technically required hardware emergency stops, temperature limiters, pressure protection, boiler safety chains, electrical protection or manufacturer safety controls.

## Fail-safe direction

The architecture follows these principles:

- missing/invalid critical data must not create aggressive new control actions
- safety/technical constraints outrank mandatory and optimization strategies
- plugins report communication degradation rather than invent values
- physical writes are explicit canonical commands
- write capability must be declared by the plugin manifest
- software emergency stop blocks all normal physical commands
- future safe-state actions must be explicitly designed per capability/device class

A future distinction may be needed between **normal commands** and narrowly defined **safety shutdown commands** that are allowed during an emergency stop. This must be explicit, never implicit.

## Audit trail

The audit log records operationally significant events, including:

- plugin configured/start/start failure
- collection failures
- strategy decisions and reasons
- command attempt
- command success/failure
- command blocked by emergency stop
- emergency-stop engage/reset
- later: plugin install/update/rollback and configuration changes

V0.1 keeps an in-memory recent log and supports append-only JSONL persistence through `AuditLog(path=...)`. Production will use persistent storage by default.

Endpoint: `GET /audit?limit=100`

## Metrics

Endpoint: `GET /metrics`

Initial counters/gauges include:

- `plugin_configured_total`
- `plugin_start_success_total`
- `plugin_start_failed_total`
- `collect_success_total`
- `collect_failed_total`
- `points_ingested_total`
- `strategy_evaluation_total`
- `strategy_blocked_emergency_stop_total`
- `command_success_total`
- `command_failed_total`
- `command_blocked_emergency_stop_total`
- `emergency_stop_engaged_total`
- `emergency_stop_reset_total`
- `emergency_stop_active`
- runtime uptime

Next metric layer:
- last successful read timestamp per plugin
- data age/staleness per critical point
- read latency
- command latency
- plugin version/update state
- restart count
- decision/action counts by strategy
- remote fleet heartbeat

## Observability goal

For any relevant event INS-EI should eventually answer:

1. What was the plant state?
2. Was the data fresh and healthy?
3. Which strategies were considered?
4. Why did one strategy win?
5. Which canonical command was attempted?
6. Was it allowed by safety/capability checks?
7. Which plugin/device received it?
8. Did execution succeed?
9. What happened afterward?
