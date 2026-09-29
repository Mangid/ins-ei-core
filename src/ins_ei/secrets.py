from __future__ import annotations

import json
import os
from pathlib import Path


class SecretStore:
    """Local appliance secret store. Values never belong to SiteConfig."""

    def __init__(self, data_dir: str | Path) -> None:
        self.path = Path(data_dir) / "secrets.json"

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, key: str) -> str | None:
        return self._load().get(key)

    def set(self, key: str, value: str | None) -> None:
        data = self._load()
        if value:
            data[key] = value
        else:
            data.pop(key, None)
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.chmod(self.path, 0o600)

    def has(self, key: str) -> bool:
        return bool(self.get(key))
