from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt

log = logging.getLogger("ins_ei.bus")


class BusClient:
    """Best-effort MQTT/TLS client. Central connectivity never gates local Core."""

    def __init__(self, site_id: str, config: dict[str, Any], core_version: str = "unknown") -> None:
        self.site_id = site_id
        self.config = config
        self.core_version = core_version
        self.enabled = bool(config.get("enabled", False))
        self.connected = False
        self.sequence = 0
        self._lock = threading.Lock()
        self.client: mqtt.Client | None = None

    @property
    def base(self) -> str:
        return f"ins-ei/{self.site_id}"

    def start(self) -> None:
        if not self.enabled:
            return
        client_id = str(self.config.get("client_id") or f"ins-ei-{self.site_id}")
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        username = self.config.get("username")
        if username:
            self.client.username_pw_set(str(username), str(self.config.get("password") or ""))
        if bool(self.config.get("tls", True)):
            self.client.tls_set()
        self.client.will_set(
            f"{self.base}/status",
            json.dumps(self._envelope("status", {"online": False})),
            qos=1, retain=True,
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.connect_async(
            str(self.config["host"]), int(self.config.get("port", 8883)),
            keepalive=int(self.config.get("keepalive", 60)),
        )
        self.client.loop_start()

    def stop(self) -> None:
        if not self.client:
            return
        try:
            if self.connected:
                self.publish("status", "status", {"online": False}, retain=True)
            self.client.disconnect()
            self.client.loop_stop()
        except Exception:
            log.exception("mqtt stop failed")

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        self.connected = reason_code == 0
        if self.connected:
            log.info("mqtt connected | site=%s host=%s", self.site_id, self.config.get("host"))
            self.publish("status", "status", {"online": True}, retain=True)
        else:
            log.warning("mqtt connect failed | site=%s reason=%s", self.site_id, reason_code)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        self.connected = False
        log.warning("mqtt disconnected | site=%s reason=%s", self.site_id, reason_code)

    def _envelope(self, type_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.sequence += 1
            sequence = self.sequence
        return {
            "api_version": "ins-ei.bus/v1",
            "site_id": self.site_id,
            "type": type_name,
            "generated_at": datetime.now().astimezone().isoformat(),
            "sequence": sequence,
            "core_version": self.core_version,
            "payload": payload,
        }

    def publish(self, topic: str, type_name: str, payload: dict[str, Any], retain: bool = False) -> bool:
        if not self.enabled or not self.client or not self.connected:
            return False
        try:
            data = json.dumps(self._envelope(type_name, payload), ensure_ascii=False, separators=(",", ":"))
            info = self.client.publish(f"{self.base}/{topic}", data, qos=1, retain=retain)
            return info.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception:
            log.exception("mqtt publish failed | site=%s topic=%s", self.site_id, topic)
            return False
