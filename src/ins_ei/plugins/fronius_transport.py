from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import urlopen


class FroniusTransport:
    """Read-only local Fronius Solar API V1 transport."""

    def __init__(self, host: str, timeout: float = 5.0) -> None:
        self.host = host.strip().rstrip("/")
        self.timeout = float(timeout)

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        query = ("?" + urlencode(params)) if params else ""
        url = f"http://{self.host}/solar_api/v1/{endpoint}{query}"
        with urlopen(url, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        head = data.get("Head", {})
        status = head.get("Status", {})
        if status.get("Code", 0) not in (0, None):
            raise RuntimeError(f"FRONIUS_API:{status.get('Code')}:{status.get('Reason','')}")
        return data

    def power_flow(self) -> dict:
        return self._get("GetPowerFlowRealtimeData.fcgi")

    def inverter_common(self, device_id: int = 1) -> dict:
        return self._get("GetInverterRealtimeData.cgi", {
            "Scope": "Device",
            "DeviceId": int(device_id),
            "DataCollection": "CommonInverterData",
        })

    def inverter_three_phase(self, device_id: int = 1) -> dict:
        return self._get("GetInverterRealtimeData.cgi", {
            "Scope": "Device",
            "DeviceId": int(device_id),
            "DataCollection": "3PInverterData",
        })
