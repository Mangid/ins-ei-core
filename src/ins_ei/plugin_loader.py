from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ins_ei.plugins.base import Plugin


class PluginPermissions(BaseModel):
    network: bool = False
    filesystem: bool = False


class PluginManifest(BaseModel):
    api_version: str
    id: str
    name: str
    version: str
    kind: str
    entrypoint: str
    capabilities: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    permissions: PluginPermissions = Field(default_factory=PluginPermissions)
    notes: dict[str, Any] = Field(default_factory=dict)


class InstalledPlugin(BaseModel):
    manifest: PluginManifest
    manifest_path: Path


class PluginCatalog:
    def __init__(self, plugin_dir: str | Path) -> None:
        self.plugin_dir = Path(plugin_dir)
        self._plugins: dict[str, InstalledPlugin] = {}

    def discover(self) -> dict[str, InstalledPlugin]:
        discovered: dict[str, InstalledPlugin] = {}
        if not self.plugin_dir.exists():
            self._plugins = {}
            return self._plugins

        for manifest_path in sorted(self.plugin_dir.glob("*/manifest.yaml")):
            data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            manifest = PluginManifest.model_validate(data)
            if manifest.api_version != "ins-ei.plugin/v1":
                raise ValueError(
                    f"Unsupported plugin api_version for {manifest.id}: {manifest.api_version}"
                )
            if manifest.id in discovered:
                raise ValueError(f"Duplicate plugin id: {manifest.id}")
            discovered[manifest.id] = InstalledPlugin(
                manifest=manifest,
                manifest_path=manifest_path,
            )

        self._plugins = discovered
        return dict(self._plugins)

    def installed(self) -> dict[str, InstalledPlugin]:
        return dict(self._plugins)

    def manifest(self, plugin_id: str) -> PluginManifest:
        try:
            return self._plugins[plugin_id].manifest
        except KeyError as exc:
            raise ValueError(f"Plugin not installed: {plugin_id}") from exc

    def create(self, plugin_id: str, instance_id: str, config: dict[str, Any]) -> Plugin:
        manifest = self.manifest(plugin_id)
        try:
            module_name, class_name = manifest.entrypoint.split(":", 1)
        except ValueError as exc:
            raise ValueError(f"Invalid entrypoint for {plugin_id}: {manifest.entrypoint}") from exc

        module = importlib.import_module(module_name)
        plugin_class = getattr(module, class_name, None)
        if plugin_class is None:
            raise ValueError(f"Entrypoint class not found: {manifest.entrypoint}")
        if not isinstance(plugin_class, type) or not issubclass(plugin_class, Plugin):
            raise TypeError(f"Entrypoint must implement Plugin: {manifest.entrypoint}")
        return plugin_class(instance_id, config)
