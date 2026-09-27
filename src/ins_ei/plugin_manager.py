from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ins_ei.plugin_loader import PluginManifest


@dataclass(frozen=True)
class InstallResult:
    plugin_id: str
    version: str
    previous_version: str | None
    backup_created: bool


class PluginManager:
    """Transactional local plugin package installer.

    Remote transport is deliberately separate. This class installs an already
    downloaded/extracted package after validation and can roll back locally.
    """

    def __init__(self, plugin_dir: str | Path, backup_dir: str | Path | None = None) -> None:
        self.plugin_dir = Path(plugin_dir)
        self.backup_dir = Path(backup_dir or (self.plugin_dir.parent / "plugin_backups"))
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _read_manifest(package_dir: Path) -> PluginManifest:
        manifest_path = package_dir / "manifest.yaml"
        if not manifest_path.is_file():
            raise ValueError("PLUGIN_MANIFEST_MISSING")
        manifest = PluginManifest.model_validate(
            yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        )
        if manifest.api_version != "ins-ei.plugin/v1":
            raise ValueError(f"PLUGIN_API_UNSUPPORTED:{manifest.api_version}")
        return manifest

    @staticmethod
    def directory_checksum(package_dir: str | Path) -> str:
        root = Path(package_dir)
        digest = hashlib.sha256()
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = path.relative_to(root).as_posix().encode()
            digest.update(len(rel).to_bytes(4, "big"))
            digest.update(rel)
            content = path.read_bytes()
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
        return digest.hexdigest()

    def installed_manifest(self, plugin_id: str) -> PluginManifest | None:
        path = self.plugin_dir / plugin_id
        if not path.is_dir():
            return None
        return self._read_manifest(path)

    def install_from_directory(
        self,
        package_dir: str | Path,
        expected_sha256: str | None = None,
    ) -> InstallResult:
        source = Path(package_dir)
        manifest = self._read_manifest(source)

        if expected_sha256:
            actual = self.directory_checksum(source)
            if actual.lower() != expected_sha256.lower():
                raise ValueError("PLUGIN_CHECKSUM_MISMATCH")

        target = self.plugin_dir / manifest.id
        previous = self.installed_manifest(manifest.id)
        backup_created = False
        backup = self.backup_dir / manifest.id

        with tempfile.TemporaryDirectory(dir=self.plugin_dir.parent) as tmp:
            staged = Path(tmp) / manifest.id
            shutil.copytree(source, staged)

            # Validate the staged copy again before touching the live plugin.
            staged_manifest = self._read_manifest(staged)
            if staged_manifest.id != manifest.id or staged_manifest.version != manifest.version:
                raise ValueError("PLUGIN_STAGING_VALIDATION_FAILED")

            if backup.exists():
                shutil.rmtree(backup)
            if target.exists():
                shutil.copytree(target, backup)
                backup_created = True

            try:
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(staged, target)
                self._read_manifest(target)
            except Exception:
                if target.exists():
                    shutil.rmtree(target)
                if backup_created and backup.exists():
                    shutil.copytree(backup, target)
                raise

        return InstallResult(
            plugin_id=manifest.id,
            version=manifest.version,
            previous_version=previous.version if previous else None,
            backup_created=backup_created,
        )

    def rollback(self, plugin_id: str) -> PluginManifest:
        backup = self.backup_dir / plugin_id
        if not backup.is_dir():
            raise ValueError("PLUGIN_ROLLBACK_NOT_AVAILABLE")
        self._read_manifest(backup)

        target = self.plugin_dir / plugin_id
        failed = self.backup_dir / f"{plugin_id}.failed"
        if failed.exists():
            shutil.rmtree(failed)
        if target.exists():
            shutil.move(str(target), str(failed))
        shutil.copytree(backup, target)
        return self._read_manifest(target)


class ManagedPluginUpdate:
    """Coordinates package replacement with a running INS-EI Runtime."""

    def __init__(self, manager: PluginManager) -> None:
        self.manager = manager

    def apply_directory(self, runtime, plugin_id: str, package_dir: str | Path,
                        expected_sha256: str | None = None) -> InstallResult:
        affected = [
            (instance_id, managed)
            for instance_id, managed in runtime.plugins.items()
            if runtime.instance_plugin_ids.get(instance_id) == plugin_id
        ]

        for _, managed in affected:
            managed.plugin.stop()

        try:
            result = self.manager.install_from_directory(package_dir, expected_sha256)
            runtime.reload_plugin_type(plugin_id)
            for instance_id, _ in affected:
                runtime.start_instance(instance_id)
                runtime.collect_instance(instance_id)
                status = runtime.plugins[instance_id].status
                if str(status) not in {"RUNNING", "PluginStatus.RUNNING"}:
                    raise RuntimeError(f"PLUGIN_POST_UPDATE_HEALTH:{instance_id}:{status}")
            return result
        except Exception:
            try:
                self.manager.rollback(plugin_id)
                runtime.reload_plugin_type(plugin_id)
                for instance_id, _ in affected:
                    runtime.start_instance(instance_id)
            except Exception:
                pass
            raise


class RemoteCatalog:
    """Parser for the server-side plugin catalog contract."""

    def __init__(self, data: dict[str, Any]) -> None:
        if data.get("api_version") != "ins-ei.catalog/v1":
            raise ValueError("PLUGIN_CATALOG_API_UNSUPPORTED")
        self.data = data

    @classmethod
    def from_json(cls, payload: str) -> "RemoteCatalog":
        return cls(json.loads(payload))

    def release(self, plugin_id: str) -> dict[str, Any]:
        for plugin in self.data.get("plugins", []):
            if plugin.get("id") == plugin_id:
                return plugin
        raise ValueError(f"PLUGIN_NOT_IN_CATALOG:{plugin_id}")
