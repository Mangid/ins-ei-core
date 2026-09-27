from __future__ import annotations

from fastapi import FastAPI

from .runtime import Runtime


def create_app(runtime: Runtime) -> FastAPI:
    app = FastAPI(title="INS-EI", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return runtime.health()

    @app.get("/safety")
    def safety() -> dict:
        state = runtime.safety.state()
        return {
            "emergency_stop": state.emergency_stop,
            "reason": state.reason,
            "changed_at": state.changed_at.isoformat(),
        }

    @app.post("/safety/emergency-stop")
    def emergency_stop(reason: str = "manual emergency stop") -> dict:
        state = runtime.safety.engage(reason)
        runtime.metrics.inc("emergency_stop_engaged_total")
        runtime.metrics.set("emergency_stop_active", 1)
        runtime.audit.record("safety.emergency_stop_engaged", reason=state.reason)
        return {"emergency_stop": True, "reason": state.reason}

    @app.post("/safety/reset")
    def safety_reset(reason: str = "manual reset") -> dict:
        state = runtime.safety.release(reason)
        runtime.metrics.inc("emergency_stop_reset_total")
        runtime.metrics.set("emergency_stop_active", 0)
        runtime.audit.record("safety.emergency_stop_reset", reason=reason)
        return {"emergency_stop": False, "reason": state.reason}

    @app.get("/metrics")
    def metrics() -> dict:
        return runtime.metrics.snapshot()

    @app.get("/audit")
    def audit(limit: int = 100) -> dict:
        return {
            "events": [
                {
                    "timestamp": e.timestamp,
                    "event": e.event,
                    "site": e.site,
                    "data": e.data,
                }
                for e in runtime.audit.recent(min(max(limit, 1), 1000))
            ]
        }

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
            "points": [
                {
                    **p.model_dump(mode="json"),
                    "age_seconds": runtime.state.age_seconds(p),
                    "stale_after_seconds": runtime.state.stale_after_seconds(p.component_id, p.point),
                }
                for p in runtime.state.snapshot()
            ],
        }

    @app.post("/collect")
    def collect() -> dict:
        runtime.collect_once()
        return {"collected": True, "points": len(runtime.state.snapshot())}

    return app
