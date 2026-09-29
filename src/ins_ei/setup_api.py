from __future__ import annotations

from typing import Any
import time

from fastapi import APIRouter, HTTPException

from ins_ei.plugin_loader import PluginCatalog
from ins_ei.setup_store import SetupStore
from ins_ei.config import SiteConfig
from ins_ei.secrets import SecretStore
from ins_ei.bus import BusClient



def _infer_components(points) -> list[dict[str, Any]]:
    kinds = {
        "power_to_heat": "POWER_TO_HEAT",
        "pellet_boiler": "HEAT_GENERATOR",
        "buffer": "BUFFER",
        "dhw": "DHW",
        "grid": "GRID",
        "weather": "WEATHER",
        "battery": "BATTERY",
        "pv": "PV",
        "hk1": "HEATING_CIRCUIT",
        "hk2": "HEATING_CIRCUIT",
    }
    component_ids = sorted({p.component_id for p in points})
    result = []
    for component_id in component_ids:
        kind = kinds.get(component_id)
        if kind is None:
            # Point-prefix fallback for future plugins; explicit plugin discovery
            # metadata will supersede this V1 inference.
            point_names = [p.point for p in points if p.component_id == component_id]
            if any(x.startswith("battery.") for x in point_names):
                kind = "BATTERY"
            elif any(x.startswith("pv.") for x in point_names):
                kind = "PV_INVERTER" if any(x.startswith("electrical.") for x in point_names) else "PV"
            elif any(x.startswith("grid.") for x in point_names):
                kind = "GRID"
            elif any(x.startswith("electrical.") for x in point_names) and component_id.startswith("grid"):
                kind = "GRID"
        result.append({
            "id": component_id,
            "kind": kind,
            "ready": kind is not None,
        })
    return result


def create_setup_router(catalog: PluginCatalog, store: SetupStore) -> APIRouter:
    router = APIRouter(prefix="/setup", tags=["setup"])
    secrets = SecretStore(store.data_dir)

    @router.get("/status")
    def status():
        return {"configured": store.exists(), "site_path": str(store.site_path), "central_password_configured": secrets.has("central.mqtt_password")}

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
                "components": (
                    plugin.discover_components(points)
                    if plugin.discover_components(points)
                    else _infer_components(points)
                ),
                "diagnostics": diagnostics,
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        finally:
            try:
                plugin.stop()
            except Exception:
                pass


    @router.post("/test-central")
    def test_central(payload: dict[str, Any]):
        config = {
            "enabled": True,
            "host": str(payload.get("host") or "").strip(),
            "port": int(payload.get("port") or 8883),
            "tls": bool(payload.get("tls", True)),
            "username": str(payload.get("username") or "").strip(),
            "password": str(payload.get("password") or secrets.get("central.mqtt_password") or ""),
        }
        if not config["host"] or not config["username"] or not config["password"]:
            raise HTTPException(400, "CENTRAL_MQTT_CONFIG_INCOMPLETE")
        client = BusClient(str(payload.get("site_id") or "setup-test"), config, "setup-test")
        client.start()
        deadline=time.monotonic()+6.0
        try:
            while time.monotonic()<deadline and not client.connected:
                time.sleep(.1)
            if not client.connected:
                raise HTTPException(400, "CENTRAL_MQTT_CONNECTION_FAILED")
            return {"ok":True,"host":config["host"],"port":config["port"],"tls":config["tls"]}
        finally:
            client.stop()

    @router.post("/save")
    def save(payload: dict[str, Any]):
        site = {
            "api_version": "ins-ei.site/v1",
            "site": {
                "id": payload.get("site_id") or "ins-ei-site",
                "timezone": payload.get("timezone") or "Europe/Vienna",
                "location": payload.get("location") or {},
            },
            "plugin_instances": payload.get("plugin_instances") or [],
            "components": payload.get("components") or [],
            "relations": payload.get("relations") or [],
            "connections": payload.get("connections") or [],
            "constraints": payload.get("constraints") or [],
            "apps": payload.get("apps") or {},
            "central": payload.get("central") or {},
            "strategy": payload.get("strategy") or {"modules": []},
            "site_rules": payload.get("site_rules") or [],
            "commissioning": payload.get("commissioning") or {},
        }
        central_password = str(payload.get("central_password") or "")
        # Validate the exact document before touching the persistent Site.
        validated = SiteConfig.model_validate(site)
        path = store.save(validated.model_dump(mode="json"))
        if central_password:
            secrets.set("central.mqtt_password", central_password)
        persisted = store.load()
        if persisted is None:
            raise HTTPException(status_code=500, detail="SITE_SAVE_VERIFY_FAILED")
        # Read-after-write verification prevents false-positive save feedback.
        verified = SiteConfig.model_validate(persisted)
        return {
            "saved": True,
            "saved_plugins": [
                {"plugin": x.plugin, "config_keys": sorted(x.config.keys())}
                for x in verified.plugin_instances
            ],
            "verified": True,
            "path": str(path),
            "restart_required": True,
            "site": verified.model_dump(mode="json"),
        }

    return router
