from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Quality(StrEnum):
    GOOD = "GOOD"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


class PluginStatus(StrEnum):
    CONFIGURED = "CONFIGURED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


class Source(BaseModel):
    plugin_instance: str


class Point(BaseModel):
    component_id: str
    point: str
    value: Any
    unit: str | None = None
    quality: Quality = Quality.GOOD
    observed_at: datetime
    source: Source


class PluginHealth(BaseModel):
    status: PluginStatus
    message: str = "OK"
    checked_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())
