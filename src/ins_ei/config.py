from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SiteInfo(BaseModel):
    id: str
    timezone: str = "Europe/Vienna"


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


def load_site(path: str | Path) -> SiteConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    site = SiteConfig.model_validate(data)
    if site.api_version != "ins-ei.site/v1":
        raise ValueError(f"Unsupported site api_version: {site.api_version}")
    return site
