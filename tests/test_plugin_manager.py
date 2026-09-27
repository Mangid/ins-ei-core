from pathlib import Path

import pytest

from ins_ei.plugin_manager import PluginManager, RemoteCatalog


def write_plugin(root: Path, plugin_id: str, version: str) -> Path:
    path = root / f"{plugin_id}-{version}"
    path.mkdir()
    (path / "manifest.yaml").write_text(
        f"""api_version: ins-ei.plugin/v1
id: {plugin_id}
name: Test
version: {version}
kind: device
entrypoint: ins_ei.plugins.demo:DemoPlugin
capabilities: []
permissions:
  network: false
  filesystem: false
""",
        encoding="utf-8",
    )
    (path / "payload.txt").write_text(version, encoding="utf-8")
    return path


def test_install_update_and_rollback(tmp_path):
    packages = tmp_path / "packages"
    packages.mkdir()
    plugins = tmp_path / "plugins"
    manager = PluginManager(plugins)

    v1 = write_plugin(packages, "test", "1.0.0")
    result1 = manager.install_from_directory(v1)
    assert result1.previous_version is None
    assert manager.installed_manifest("test").version == "1.0.0"

    v2 = write_plugin(packages, "test", "2.0.0")
    result2 = manager.install_from_directory(v2)
    assert result2.previous_version == "1.0.0"
    assert result2.backup_created
    assert manager.installed_manifest("test").version == "2.0.0"

    restored = manager.rollback("test")
    assert restored.version == "1.0.0"


def test_checksum_blocks_modified_package(tmp_path):
    package = write_plugin(tmp_path, "test", "1.0.0")
    manager = PluginManager(tmp_path / "live")
    with pytest.raises(ValueError, match="PLUGIN_CHECKSUM_MISMATCH"):
        manager.install_from_directory(package, expected_sha256="0" * 64)


def test_remote_catalog_contract():
    catalog = RemoteCatalog({
        "api_version": "ins-ei.catalog/v1",
        "plugins": [{"id": "oekofen", "version": "1.2.3"}],
    })
    assert catalog.release("oekofen")["version"] == "1.2.3"
