from __future__ import annotations

from fastapi import FastAPI

from .runtime import Runtime


def create_app(runtime: Runtime) -> FastAPI:
    app = FastAPI(title="INS-EI", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return runtime.health()

    @app.get("/plugins")
    def plugins() -> dict:
        return {
            "plugins": [
                item.manifest.model_dump(mode="json")
                for item in runtime.catalog.installed().values()
            ]
        }

    @app.get("/state")
    def state() -> dict:
        return {
            "site": runtime.site.site.id,
            "points": [p.model_dump(mode="json") for p in runtime.state.snapshot()],
        }

    @app.post("/collect")
    def collect() -> dict:
        runtime.collect_once()
        return {"collected": True, "points": len(runtime.state.snapshot())}

    return app
