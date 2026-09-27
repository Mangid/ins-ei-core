from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

RATE_LIMIT_TEXT = "wait at least 2500ms"


class OekofenTransport:
    """Low-level ÖkoFEN JSON interface. No INS-EI strategy belongs here."""

    def __init__(self, host: str, password: str, port: int = 4321, timeout: float = 10.0) -> None:
        self.host = host.strip()
        self.password = password
        self.port = int(port)
        self.timeout = float(timeout)
        self._last_request = 0.0
        self.min_request_interval = 2.6

    def _wait_rate_limit(self) -> None:
        remaining = self.min_request_interval - (time.monotonic() - self._last_request)
        if remaining > 0:
            time.sleep(remaining)

    def _request(self, path: str) -> bytes:
        self._wait_rate_limit()
        url = f"http://{self.host}:{self.port}/{self.password}/{path}"
        req = Request(url, headers={"Accept": "application/json", "Connection": "close"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                body, status = response.read(), response.status
        except HTTPError as exc:
            body, status = exc.read(), exc.code
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"OEKOFEN_HTTP:{type(exc).__name__}") from exc
        finally:
            self._last_request = time.monotonic()

        text = self._decode(body)
        if RATE_LIMIT_TEXT in text.strip().lower():
            raise RuntimeError("OEKOFEN_REQUEST_ABSTAND")
        if status != 200:
            raise RuntimeError(f"OEKOFEN_HTTP_{status}")
        return body

    @staticmethod
    def _decode(body: bytes) -> str:
        for encoding in ("utf-8", "cp1252", "latin-1"):
            try:
                return body.decode(encoding)
            except UnicodeDecodeError:
                continue
        return ""

    def read_all(self) -> dict:
        body = self._request("all")
        try:
            data = json.loads(self._decode(body))
        except json.JSONDecodeError as exc:
            raise RuntimeError("OEKOFEN_JSON_INVALID") from exc
        if not isinstance(data, dict):
            raise RuntimeError("OEKOFEN_JSON_NOT_OBJECT")
        return data

    def set_value(self, section: str, variable: str, value: object) -> str:
        allowed = {("pe1", "mode"), ("ww1", "heat_once")}
        if (section, variable) not in allowed:
            raise RuntimeError("OEKOFEN_WRITE_NOT_ALLOWED")
        path = f"{quote(section)}.{quote(variable)}={quote(str(value))}"
        return self._decode(self._request(path))
