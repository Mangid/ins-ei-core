from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SiteLocation(BaseModel):
    name: str | None = None
    postal_code: str | None = None
    country: str = "AT"
    latitude: float | None = None
    longitude: float | None = None


class SiteInfo(BaseModel):
    id: str
    timezone: str = "Europe/Vienna"
    location: SiteLocation = Field(default_factory=SiteLocation)


class PluginInstanceConfig(BaseModel):
    id: str
    plugin: str
    config: dict[str, Any] = Field(default_factory=dict)


class PortConfig(BaseModel):
    id: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class SensorPositionConfig(BaseModel):
    id: str
    point: str | None = None
    position: float | None = None
    port: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class ComponentConfig(BaseModel):
    id: str
    kind: str
    provider: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    ports: list[PortConfig] = Field(default_factory=list)
    sensors: list[SensorPositionConfig] = Field(default_factory=list)


class CommissioningConfig(BaseModel):
    status: str = "DRAFT"
    confirmed_at: str | None = None
    confirmed_by: str | None = None
    topology_confirmed: bool = False
    constraints_confirmed: bool = False
    notes: list[str] = Field(default_factory=list)


class SiteConfig(BaseModel):
    api_version: str
    site: SiteInfo
    plugin_instances: list[PluginInstanceConfig] = Field(default_factory=list)
    components: list[ComponentConfig] = Field(default_factory=list)
    relations: list[dict[str, Any]] = Field(default_factory=list)
    connections: list[dict[str, Any]] = Field(default_factory=list)
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    apps: dict[str, Any] = Field(default_factory=dict)
    strategy: dict[str, Any] = Field(default_factory=dict)
    site_rules: list[dict[str, Any]] = Field(default_factory=list)
    commissioning: CommissioningConfig = Field(default_factory=CommissioningConfig)


def load_site(path: str | Path) -> SiteConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    site = SiteConfig.model_validate(data)
    if site.api_version != "ins-ei.site/v1":
        raise ValueError(f"Unsupported site api_version: {site.api_version}")
    return site
