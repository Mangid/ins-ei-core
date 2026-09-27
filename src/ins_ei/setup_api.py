from __future__ import annotations

from typing import Any
import time

from fastapi import APIRouter, HTTPException

from ins_ei.plugin_loader import PluginCatalog
from ins_ei.setup_store import SetupStore


def create_setup_router(catalog: PluginCatalog, store: SetupStore) -> APIRouter:
    router = APIRouter(prefix="/setup", tags=["setup"])

    @router.get("/status")
    def status():
        return {"configured": store.exists(), "site_path": str(store.site_path)}

    @router.get("/plugins")
    def plugins():
        return {
            "plugins": [
                {
                    "id": item.manifest.id,
                    "name": item.manifest.name,
                    "version": item.manifest.version,
                    "capabilities": item.manifest.capabilities,
                    "commands": item.manifest.commands,
                    "config_schema": item.manifest.config_schema,
                }
                for item in catalog.installed().values()
                if item.manifest.kind != "test"
            ]
        }

    @router.post("/test-plugin")
    def test_plugin(payload: dict[str, Any]):
        plugin_id = str(payload.get("plugin_id", ""))
        instance_id = str(payload.get("instance_id", "setup_test"))
        config = dict(payload.get("config") or {})
        plugin = catalog.create(plugin_id, instance_id, config)
        try:
            plugin.validate_config()
            plugin.start()
            # Network plugins such as MQTT may need a short discovery window.
            points = []
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                points = plugin.read_points()
                if points:
                    break
                time.sleep(0.25)
            health = plugin.health()
            diagnostics = (
                plugin.diagnostics()
                if hasattr(plugin, "diagnostics")
                else {}
            )
            return {
                "ok": (
                    str(health.status) in {"RUNNING", "PluginStatus.RUNNING"}
                    and len(points) > 0
                ),
                "health": health.model_dump(mode="json"),
                "points": [p.model_dump(mode="json") for p in points],
                "diagnostics": diagnostics,
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        finally:
            try:
                plugin.stop()
            except Exception:
                pass

    @router.post("/save")
    def save(payload: dict[str, Any]):
        site = {
            "api_version": "ins-ei.site/v1",
            "site": {
                "id": payload.get("site_id") or "ins-ei-site",
                "timezone": payload.get("timezone") or "Europe/Vienna",
            },
            "plugin_instances": payload.get("plugin_instances") or [],
            "components": payload.get("components") or [],
            "relations": payload.get("relations") or [],
            "connections": payload.get("connections") or [],
            "constraints": payload.get("constraints") or [],
            "apps": payload.get("apps") or {},
            "strategy": payload.get("strategy") or {"modules": []},
            "site_rules": payload.get("site_rules") or [],
        }
        path = store.save(site)
        return {
            "saved": True,
            "path": str(path),
            "restart_required": True,
        }

    return router
