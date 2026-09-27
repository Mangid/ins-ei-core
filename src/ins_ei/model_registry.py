from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ModelStatus(StrEnum):
    LEARNING = "LEARNING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    INVALIDATED = "INVALIDATED"


@dataclass(frozen=True)
class ModelDependency:
    kind: str
    id: str
    version: str | None = None


@dataclass
class LearningModelRecord:
    id: str
    version: str
    capability: str
    status: ModelStatus = ModelStatus.LEARNING
    dependencies: list[ModelDependency] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    status_changed_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    metadata: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, LearningModelRecord] = {}

    def register(self, model: LearningModelRecord) -> None:
        existing = self._models.get(model.id)
        if existing and existing.version == model.version:
            raise ValueError(f"MODEL_ALREADY_REGISTERED:{model.id}:{model.version}")
        self._models[model.id] = model

    def get(self, model_id: str) -> LearningModelRecord:
        try:
            return self._models[model_id]
        except KeyError as exc:
            raise ValueError(f"MODEL_UNKNOWN:{model_id}") from exc

    def all(self) -> list[LearningModelRecord]:
        return list(self._models.values())

    def set_status(self, model_id: str, status: ModelStatus, reason: str) -> LearningModelRecord:
        model = self.get(model_id)
        model.status = status
        model.reason = reason
        model.status_changed_at = datetime.now().astimezone()
        return model

    def invalidate_dependency(self, kind: str, dependency_id: str, reason: str) -> list[str]:
        affected = []
        for model in self._models.values():
            if any(d.kind == kind and d.id == dependency_id for d in model.dependencies):
                self.set_status(model.id, ModelStatus.INVALIDATED, reason)
                affected.append(model.id)
        return affected
