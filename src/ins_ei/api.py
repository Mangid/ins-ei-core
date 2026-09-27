from __future__ import annotations

from fastapi import FastAPI

from .runtime import Runtime


def create_app(runtime: Runtime) -> FastAPI:
    app = FastAPI(title="INS-EI", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return runtime.health()

    @app.post("/strategy/evaluate")
    def evaluate_strategy() -> dict:
        decision = runtime.evaluate_strategy()
        return {
            "action": decision.action,
            "reason": decision.reason,
            "winning_strategy": decision.winning_strategy,
            "priority": decision.priority.name,
            "confidence": decision.confidence,
            "intents": [
                {"target": i.target, "command": i.command, "parameters": i.parameters}
                for i in decision.intents
            ],
            "considered": [
                {
                    "strategy": p.strategy,
                    "action": p.action,
                    "priority": p.priority.name,
                    "reason": p.reason,
                    "confidence": p.confidence,
                    "evidence": p.evidence,
                }
                for p in decision.considered
            ],
            "decided_at": decision.decided_at.isoformat(),
        }

    @app.get("/site")
    def site() -> dict:
        return runtime.graph.describe()

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
