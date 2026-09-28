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

    def inverter_cumulation(self, device_id: int = 1) -> dict:
        return self._get("GetInverterRealtimeData.cgi", {
            "Scope": "Device",
            "DeviceId": int(device_id),
            "DataCollection": "CumulationInverterData",
        })

    def inverter_minmax(self, device_id: int = 1) -> dict:
        return self._get("GetInverterRealtimeData.cgi", {
            "Scope": "Device",
            "DeviceId": int(device_id),
            "DataCollection": "MinMaxInverterData",
        })

    def inverter_three_phase(self, device_id: int = 1) -> dict:
        return self._get("GetInverterRealtimeData.cgi", {
            "Scope": "Device",
            "DeviceId": int(device_id),
            "DataCollection": "3PInverterData",
        })


    def archive_strings_today(self) -> dict:
        from datetime import date
        d = date.today()
        date_text = f"{d.day}.{d.month}.{d.year}"
        # Repeated Channel query parameters are required by the Fronius API.
        channels = [
            "Current_DC_String_1", "Current_DC_String_2",
            "Voltage_DC_String_1", "Voltage_DC_String_2",
            "Temperature_Powerstage",
        ]
        query = "&".join([
            "Scope=System",
            f"StartDate={date_text}",
            f"EndDate={date_text}",
            *[f"Channel={name}" for name in channels],
        ])
        url = f"http://{self.host}/solar_api/v1/GetArchiveData.cgi?{query}"
        with urlopen(url, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        head = data.get("Head", {})
        status = head.get("Status", {})
        if status.get("Code", 0) not in (0, None):
            raise RuntimeError(f"FRONIUS_ARCHIVE:{status.get('Code')}:{status.get('Reason','')}")
        return data
