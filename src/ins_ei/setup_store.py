from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class SetupStore:
    """Persistent local site configuration used by the first-run wizard."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.site_path = self.data_dir / "site.yaml"

    def exists(self) -> bool:
        return self.site_path.is_file()

    def load(self) -> dict[str, Any] | None:
        if not self.exists():
            return None
        return yaml.safe_load(self.site_path.read_text(encoding="utf-8"))

    def save(self, site: dict[str, Any]) -> Path:
        # Local file only; never written to repository.
        self.site_path.write_text(
            yaml.safe_dump(site, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return self.site_path
