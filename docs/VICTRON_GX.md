# Victron GX V1 Shadow Adapter

The first Victron provider is intentionally read-only.

It connects directly to the local GX/Venus OS MQTT broker and normalizes:
- battery SOC
- signed Victron battery power into separate charge/discharge power
- PV power

No Home Assistant entity is required.

## GX preparation

Enable local MQTT access on the GX device under its Integrations settings. Use the site's selected security profile and network policy.

The initial V1 example uses local port 1883 only as a deployment template. Production security settings must match the actual GX configuration and trusted LAN.

## Why read-only first

Battery/ESS control is safety- and system-mode-sensitive. V1 Shadow must first prove:
- correct source/device selection
- correct power sign
- SOC source
- PV aggregation
- freshness/heartbeat behavior
- historical data quality

Only then will a separate proven command implementation declare `battery.set_charge_power` / discharge/export capabilities.

This preserves the INS-EI rule: Strategy may propose before the device plugin is permitted to write.
