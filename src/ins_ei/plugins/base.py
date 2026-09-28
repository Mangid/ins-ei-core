from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ins_ei.models import PluginHealth, Point


class Plugin(ABC):
    def __init__(self, instance_id: str, config: dict[str, Any]) -> None:
        self.instance_id = instance_id
        self.config = config

    @property
    def min_poll_interval_seconds(self) -> float:
        return float(self.config.get("poll_interval_seconds", 0.0))

    @abstractmethod
    def validate_config(self) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def health(self) -> PluginHealth: ...

    @abstractmethod
    def read_points(self) -> list[Point]: ...

    def execute(self, command: str, parameters: dict[str, Any] | None = None) -> Any:
        raise NotImplementedError(f"{self.instance_id} does not support commands")
