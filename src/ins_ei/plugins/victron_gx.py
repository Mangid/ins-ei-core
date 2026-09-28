from __future__ import annotations

import json
import time
import logging
from datetime import datetime
from threading import Lock
from typing import Any

import paho.mqtt.client as mqtt

log = logging.getLogger("ins_ei.plugin.victron_gx")

from ins_ei.models import PluginHealth, PluginStatus, Point, Quality, Source
from ins_ei.plugins.base import Plugin


class VictronGXPlugin(Plugin):
    """Read-only local Victron GX MQTT adapter for V1 Shadow operation."""

    def __init__(self, instance_id: str, config: dict[str, Any]) -> None:
        super().__init__(instance_id, config)
        self.client: mqtt.Client | None = None
        self.running = False
        self.connected = False
        self.last_error: str | None = None
        self.values: dict[str, tuple[Any, datetime]] = {}
        self.lock = Lock()
        self.message_count = 0
        self.last_wait_log = 0.0

    def validate_config(self) -> None:
        for key in ("host", "portal_id"):
            if not str(self.config.get(key, "")).strip():
                raise ValueError(f"victron_gx requires {key}")

    def start(self) -> None:
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if self.config.get("username"):
            self.client.username_pw_set(
                self.config["username"], self.config.get("password")
            )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.connect(
            self.config["host"], int(self.config.get("port", 1883)), 30
        )
        self.client.loop_start()
        self.running = True

    def stop(self) -> None:
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        self.running = False
        self.connected = False

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            self.last_error = f"VICTRON_MQTT_CONNECT:{reason_code}"
            log.warning("mqtt connect failed | instance=%s reason=%s", self.instance_id, reason_code)
            return
        self.connected = True
        portal = self.config["portal_id"]
        log.info("mqtt connected | instance=%s host=%s port=%s portal_id=%s",
                 self.instance_id, self.config.get("host"), self.config.get("port", 1883), portal)
        client.subscribe(f"N/{portal}/system/+/Dc/Battery/Soc")
        client.subscribe(f"N/{portal}/system/+/Dc/Battery/Power")
        client.subscribe(f"N/{portal}/system/+/Dc/Pv/Power")
        client.subscribe(f"N/{portal}/system/+/Ac/Grid/L1/Power")
        client.subscribe(f"N/{portal}/system/+/Ac/Grid/L2/Power")
        client.subscribe(f"N/{portal}/system/+/Ac/Grid/L3/Power")
        log.info("mqtt subscribed | instance=%s portal_id=%s topics=6", self.instance_id, portal)
        # Request retained/current values from Venus MQTT.
        client.publish(f"R/{portal}/system/0/Serial", "{}")
        self.last_error = None

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.connected = False

    def _on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            value = payload.get("value")
            if value is not None:
                with self.lock:
                    self.values[message.topic] = (value, datetime.now().astimezone())
                    self.message_count += 1
                    count = self.message_count
                if count <= 10 or count % 100 == 0:
                    log.info("mqtt message | instance=%s count=%d topic=%s", self.instance_id, count, message.topic)
        except Exception as exc:
            self.last_error = f"VICTRON_MQTT_PAYLOAD:{exc}"

    def health(self) -> PluginHealth:
        if not self.running:
            return PluginHealth(status=PluginStatus.STOPPED, message="plugin stopped")
        if self.last_error:
            return PluginHealth(status=PluginStatus.DEGRADED, message=self.last_error)
        if not self.connected:
            return PluginHealth(status=PluginStatus.DEGRADED, message="MQTT not connected")
        if not self.values:
            return PluginHealth(status=PluginStatus.STARTING, message="MQTT connected; waiting for telemetry")
        return PluginHealth(status=PluginStatus.RUNNING, message="Victron GX MQTT telemetry active")

    def _latest_suffix(self, suffix: str):
        with self.lock:
            matches = [(v, ts) for topic, (v, ts) in self.values.items() if topic.endswith(suffix)]
        return max(matches, key=lambda x: x[1]) if matches else None

    def read_points(self) -> list[Point]:
        source = Source(plugin_instance=self.instance_id)
        if self.connected and not self.values:
            now_mono = time.monotonic()
            if now_mono - self.last_wait_log >= 30:
                log.warning(
                    "waiting for telemetry | instance=%s portal_id=%s messages=%d",
                    self.instance_id, self.config.get("portal_id"), self.message_count,
                )
                self.last_wait_log = now_mono
        battery = self.config.get("battery_component", "battery")
        pv = self.config.get("pv_component", "pv")
        specs = [
            (battery, "battery.soc", "%", "/Dc/Battery/Soc", "soc"),
            (pv, "pv.generation_power", "W", "/Dc/Pv/Power", "positive"),
        ]
        points: list[Point] = []
        for component, point, unit, suffix, mode in specs:
            item = self._latest_suffix(suffix)
            if item is None:
                continue
            value, observed = item
            value = float(value)
            if mode == "positive":
                value = max(0.0, value)
            points.append(Point(
                component_id=component, point=point, value=value, unit=unit,
                quality=Quality.GOOD, observed_at=observed, source=source,
            ))

        power = self._latest_suffix("/Dc/Battery/Power")
        if power:
            value, observed = float(power[0]), power[1]
            points.extend([
                Point(component_id=battery, point="battery.charge_power", value=max(0.0, value), unit="W", quality=Quality.GOOD, observed_at=observed, source=source),
                Point(component_id=battery, point="battery.discharge_power", value=max(0.0, -value), unit="W", quality=Quality.GOOD, observed_at=observed, source=source),
            ])
        return points

    def diagnostics(self) -> dict[str, Any]:
        with self.lock:
            topics = sorted(self.values.keys())
        return {
            "connected": self.connected,
            "topic_count": len(topics),
            "topics": topics,
            "last_error": self.last_error,
        }

    def execute(self, command: str, parameters: dict[str, Any] | None = None):
        raise NotImplementedError("Victron GX V1 Shadow plugin is read-only")
