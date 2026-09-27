from __future__ import annotations

from fastapi import FastAPI
import uvicorn

from ins_ei.plugin_loader import PluginCatalog
from ins_ei.setup_api import create_setup_router
from ins_ei.setup_store import SetupStore
from ins_ei.setup_web import setup_html


def create_setup_app(plugin_dir: str, data_dir: str) -> FastAPI:
    catalog = PluginCatalog(plugin_dir)
    catalog.discover()
    store = SetupStore(data_dir)
    app = FastAPI(title="INS-EI Setup")

    @app.get("/")
    def index():
        return setup_html(catalog.installed().values(), version="0.1.9")

    app.include_router(create_setup_router(catalog, store))
    return app


def run_setup(host: str, port: int, plugin_dir: str, data_dir: str) -> None:
    uvicorn.run(create_setup_app(plugin_dir, data_dir), host=host, port=port)
