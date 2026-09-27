from __future__ import annotations

from fastapi import FastAPI, Response

from .runtime import Runtime
from .site_view import build_site_view
from .schema_renderer import render_svg
from .outcomes import OutcomeExpectation


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

    @app.get("/learning/models")
    def learning_models() -> dict:
        return {
            "models": [
                {
                    "id": model.id,
                    "version": model.version,
                    "capability": model.capability,
                    "status": model.status,
                    "reason": model.reason,
                    "created_at": model.created_at.isoformat(),
                    "status_changed_at": model.status_changed_at.isoformat(),
                    "dependencies": [
                        {"kind": dep.kind, "id": dep.id, "version": dep.version}
                        for dep in model.dependencies
                    ],
                    "metadata": model.metadata,
                }
                for model in runtime.models.all()
            ]
        }

    @app.post("/outcomes/register")
    def register_outcome(
        correlation_id: str,
        component: str,
        point: str,
        horizon_seconds: int,
        expected_delta: float | None = None,
        expected_value: float | None = None,
        tolerance: float | None = None,
        unit: str | None = None,
        model_id: str | None = None,
        model_version: str | None = None,
    ) -> dict:
        pending = runtime.outcomes.register(OutcomeExpectation(
            correlation_id=correlation_id,
            metric_component=component,
            metric_point=point,
            horizon_seconds=horizon_seconds,
            expected_delta=expected_delta,
            expected_value=expected_value,
            tolerance=tolerance,
            unit=unit,
            model_id=model_id,
            model_version=model_version,
        ))
        return {
            "correlation_id": correlation_id,
            "due_at": pending.due_at.isoformat(),
            "baseline_value": pending.baseline_value,
        }

    @app.post("/outcomes/evaluate")
    def evaluate_outcomes() -> dict:
        results = runtime.evaluate_outcomes()
        return {"results": [result.__dict__ for result in results]}

    @app.get("/history/trace/{correlation_id}")
    def history_trace(correlation_id: str) -> dict:
        return runtime.historian.correlation(runtime.site.site.id, correlation_id)

    @app.get("/timeseries")
    def timeseries() -> dict:
        return {
            "series": {
                name: [
                    {
                        "start": slot.start.isoformat(),
                        "end": slot.end.isoformat(),
                        "value": slot.value,
                        "unit": slot.unit,
                        "quality": slot.quality,
                        "generated_at": slot.generated_at.isoformat() if slot.generated_at else None,
                        "source": slot.source,
                        "metadata": slot.metadata,
                    }
                    for slot in runtime.timeseries.series(name)
                ]
                for name in runtime.timeseries.names()
            }
        }

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

    @app.get("/site/schema.svg")
    def site_schema_svg() -> Response:
        svg = render_svg(build_site_view(runtime.graph, runtime.state))
        return Response(content=svg, media_type="image/svg+xml")

    @app.get("/site/view")
    def site_view() -> dict:
        return build_site_view(runtime.graph, runtime.state)

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
