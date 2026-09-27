from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    timestamp: str
    event: str
    site: str
    data: dict[str, Any]


class AuditLog:
    """Append-only JSONL audit trail."""

    def __init__(self, site_id: str, path: str | Path | None = None) -> None:
        self.site_id = site_id
        self.path = Path(path) if path else None
        self._events: list[AuditEvent] = []
        self._lock = RLock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, **data: Any) -> AuditEvent:
        item = AuditEvent(
            timestamp=datetime.now().astimezone().isoformat(),
            event=event,
            site=self.site_id,
            data=data,
        )
        line = json.dumps(asdict(item), ensure_ascii=False, default=str)
        with self._lock:
            self._events.append(item)
            if self.path:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
        return item

    def recent(self, limit: int = 100) -> list[AuditEvent]:
        with self._lock:
            return list(self._events[-max(1, limit):])
