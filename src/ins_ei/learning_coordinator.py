from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

from ins_ei.autonomy import AutonomyGate
from ins_ei.historian import Historian
from ins_ei.model_registry import (
    LearningModelRecord,
    ModelDependency,
    ModelRegistry,
    ModelStatus,
)
from ins_ei.config import SiteConfig
from ins_ei.readiness import (
    OutcomeEvidence,
    ReadinessAssessment,
    ReadinessPolicy,
    assess_readiness,
)


class LearningCoordinator:
    """Connects persisted outcome evidence, model readiness and autonomy."""

    def __init__(
        self,
        site_id: str,
        historian: Historian,
        models: ModelRegistry,
        autonomy: AutonomyGate,
    ) -> None:
        self.site_id = site_id
        self.historian = historian
        self.models = models
        self.autonomy = autonomy
        self.policies: dict[str, ReadinessPolicy] = {}

    def restore(self) -> None:
        for row in self.historian.load_models():
            dependencies = [
                ModelDependency(**item)
                for item in json.loads(row["dependencies_json"] or "[]")
            ]
            model = LearningModelRecord(
                id=row["model_id"],
                version=row["version"],
                capability=row["capability"],
                status=ModelStatus(row["status"]),
                dependencies=dependencies,
                created_at=datetime.fromisoformat(row["created_at"]),
                status_changed_at=datetime.fromisoformat(row["status_changed_at"]),
                metadata=json.loads(row["metadata_json"] or "{}"),
                reason=row["reason"],
            )
            self.models.register(model)
            if row["readiness_policy_json"]:
                self.policies[model.id] = ReadinessPolicy(
                    **json.loads(row["readiness_policy_json"])
                )


    def ensure_baseline_models(self, site: SiteConfig) -> None:
        """Register observation-only V1 models from the configured SiteGraph."""
        existing = {m.id for m in self.models.all()}
        kinds = {c.kind for c in site.components}
        definitions = [
            ("thermal-baseline", "thermal_behavior", {"BUFFER", "DHW", "HEAT_GENERATOR"}),
            ("electrical-baseline", "electrical_behavior", {"GRID", "PV", "BATTERY"}),
            ("battery-baseline", "battery_behavior", {"BATTERY"}),
        ]
        for model_id, capability, required_kinds in definitions:
            if model_id in existing or not (kinds & required_kinds):
                continue
            dependencies = [
                ModelDependency(kind="component", id=c.id)
                for c in site.components if c.kind in required_kinds
            ]
            model = LearningModelRecord(
                id=model_id,
                version="1",
                capability=capability,
                status=ModelStatus.LEARNING,
                dependencies=dependencies,
                metadata={"phase": "OBSERVATION", "algorithm": "baseline-v1"},
                reason="Collecting historical observations before model fitting.",
            )
            self.models.register(model)
            self.historian.save_model(model)

    def baseline_status(self) -> dict:
        summary = self.historian.observation_summary(self.site_id)
        duration_h = summary["duration_seconds"] / 3600.0
        if duration_h < 6:
            phase = "COLLECTING"
            reason = f"Collecting baseline data ({duration_h:.1f} h / 6 h minimum first assessment)."
        elif duration_h < 24:
            phase = "BASELINE_READY"
            reason = f"Initial baseline available after {duration_h:.1f} h; continue collecting for daily behavior."
        else:
            phase = "LEARNING"
            reason = f"{duration_h:.1f} h historical coverage available for model fitting."
        return {
            "phase": phase,
            "reason": reason,
            "duration_hours": duration_h,
            "signals": summary["signals"],
            "samples": summary["samples"],
            "first_observed_at": summary["first_observed_at"],
            "last_observed_at": summary["last_observed_at"],
            "coverage": summary["coverage"],
        }


    def fit_passive_baselines(self) -> dict:
        """Fit simple observation-only baselines once enough history exists."""
        status = self.baseline_status()
        if status["duration_hours"] < 6:
            return {"fitted": False, "reason": status["reason"], "models": {}}

        fitted = {}
        specs = {
            "buffer_temperature": ("buffer", "thermal.temperature_upper"),
            "dhw_temperature": ("dhw", "thermal.temperature"),
            "battery_soc": ("battery", "battery.soc"),
        }
        for name, (component, point) in specs.items():
            rows = self.historian.numeric_series(self.site_id, component, point)
            rates = []
            for a, b in zip(rows, rows[1:]):
                ta = datetime.fromisoformat(a["observed_at"])
                tb = datetime.fromisoformat(b["observed_at"])
                dt_h = (tb - ta).total_seconds() / 3600.0
                if dt_h <= 0 or dt_h > 0.25:
                    continue
                rates.append((b["value"] - a["value"]) / dt_h)
            if rows:
                values = [x["value"] for x in rows]
                fitted[name] = {
                    "samples": len(rows),
                    "minimum": min(values),
                    "maximum": max(values),
                    "mean": sum(values) / len(values),
                    "rate_samples": len(rates),
                    "mean_rate_per_hour": (sum(rates) / len(rates)) if rates else None,
                }

        for model in self.models.all():
            if model.status != ModelStatus.LEARNING:
                continue
            model.metadata["phase"] = "PASSIVE_BASELINE"
            model.metadata["last_fit_at"] = datetime.now().astimezone().isoformat()
            if model.id == "thermal-baseline":
                model.metadata["fit"] = {k: v for k, v in fitted.items() if k in {"buffer_temperature", "dhw_temperature"}}
            elif model.id == "battery-baseline":
                model.metadata["fit"] = {k: v for k, v in fitted.items() if k == "battery_soc"}
            else:
                model.metadata["fit"] = fitted
            model.reason = "Passive baseline fitted from GOOD historical observations; no control authority."
            self.historian.save_model(model)

        return {"fitted": True, "models": fitted}


    def fit_thermal_context_baseline(self) -> dict:
        """Learn context-separated buffer temperature rates without control."""
        status = self.baseline_status()
        if status["duration_hours"] < 6:
            return {"fitted": False, "reason": status["reason"]}

        buffer_rows = self.historian.numeric_series(
            self.site_id, "buffer", "thermal.temperature_upper", limit=20000
        )
        pellet_rows = self.historian.numeric_series(
            self.site_id, "pellet_boiler", "power.modulation", limit=20000
        )
        p2h_rows = self.historian.numeric_series(
            self.site_id, "power_to_heat", "power.electrical", limit=20000
        )
        outdoor_rows = self.historian.numeric_series(
            self.site_id, "weather", "weather.outdoor_temperature", limit=20000
        )

        def nearest(rows, ts, max_age_s=90):
            if not rows:
                return None
            best = min(rows, key=lambda r: abs((datetime.fromisoformat(r["observed_at"]) - ts).total_seconds()))
            age = abs((datetime.fromisoformat(best["observed_at"]) - ts).total_seconds())
            return best["value"] if age <= max_age_s else None

        buckets = {
            "PASSIVE_COOLING": [],
            "PELLET_HEATING": [],
            "POWER_TO_HEAT": [],
            "MIXED": [],
        }
        outdoor_by_bucket = {k: [] for k in buckets}
        for a, b in zip(buffer_rows, buffer_rows[1:]):
            ta = datetime.fromisoformat(a["observed_at"])
            tb = datetime.fromisoformat(b["observed_at"])
            dt_h = (tb - ta).total_seconds() / 3600.0
            if dt_h <= 0 or dt_h > 0.10:
                continue
            rate = (b["value"] - a["value"]) / dt_h
            pellet = nearest(pellet_rows, tb)
            p2h = nearest(p2h_rows, tb)
            outdoor = nearest(outdoor_rows, tb, 600)
            pellet_on = pellet is not None and pellet > 1.0
            p2h_on = p2h is not None and p2h > 100.0
            if pellet_on and p2h_on:
                bucket = "MIXED"
            elif pellet_on:
                bucket = "PELLET_HEATING"
            elif p2h_on:
                bucket = "POWER_TO_HEAT"
            else:
                bucket = "PASSIVE_COOLING"
            buckets[bucket].append(rate)
            if outdoor is not None:
                outdoor_by_bucket[bucket].append(outdoor)

        fit = {}
        for bucket, rates in buckets.items():
            if not rates:
                continue
            ordered = sorted(rates)
            fit[bucket] = {
                "samples": len(rates),
                "mean_delta_c_per_h": sum(rates) / len(rates),
                "median_delta_c_per_h": ordered[len(ordered)//2],
                "min_delta_c_per_h": ordered[0],
                "max_delta_c_per_h": ordered[-1],
                "mean_outdoor_c": (
                    sum(outdoor_by_bucket[bucket]) / len(outdoor_by_bucket[bucket])
                    if outdoor_by_bucket[bucket] else None
                ),
            }

        try:
            model = self.models.get("thermal-baseline")
        except ValueError:
            return {"fitted": False, "reason": "thermal-baseline model missing"}
        model.metadata["phase"] = "THERMAL_CONTEXT_BASELINE"
        model.metadata["thermal_context_fit"] = fit
        model.metadata["last_fit_at"] = datetime.now().astimezone().isoformat()
        model.reason = "Context-separated passive thermal baseline; no control authority."
        self.historian.save_model(model)
        return {"fitted": True, "contexts": fit}

    def register_model(
        self,
        model: LearningModelRecord,
        policy: ReadinessPolicy,
    ) -> None:
        self.models.register(model)
        self.policies[model.id] = policy
        self.historian.save_model(model, asdict(policy))

    def ingest_outcome(self, result, context_bucket: str | None = None) -> ReadinessAssessment | None:
        if not result.model_id or not result.model_version:
            return None

        self.historian.record_model_evidence(
            self.site_id,
            result.model_id,
            result.model_version,
            result.correlation_id,
            result.status,
            result.residual,
            context_bucket,
        )
        return self.reassess(result.model_id)

    def reassess(self, model_id: str) -> ReadinessAssessment:
        model = self.models.get(model_id)
        policy = self.policies.get(model_id)
        if policy is None:
            raise ValueError(f"MODEL_READINESS_POLICY_MISSING:{model_id}")

        rows = self.historian.model_evidence(
            self.site_id, model.id, model.version
        )
        evidence = [
            OutcomeEvidence(
                status=row["status"],
                residual=row["residual"],
                context_bucket=row["context_bucket"],
            )
            for row in rows
        ]
        assessment = assess_readiness(evidence, policy)

        previous = model.status
        if previous != ModelStatus.INVALIDATED:
            if assessment.status == ModelStatus.READY:
                self.models.set_status(
                    model_id, ModelStatus.READY,
                    "Readiness policy satisfied by persisted outcome evidence.",
                )
            elif previous == ModelStatus.READY:
                self.models.set_status(
                    model_id, ModelStatus.DEGRADED,
                    "; ".join(assessment.reasons) or "Readiness degraded.",
                )
                self.autonomy.degrade_for_model(
                    model_id,
                    f"Model {model_id} readiness degraded.",
                )
            else:
                self.models.set_status(
                    model_id, ModelStatus.LEARNING,
                    "; ".join(assessment.reasons) or "More evidence required.",
                )

        self.historian.save_model(
            self.models.get(model_id), asdict(policy)
        )
        self.historian.record_event(
            self.site_id,
            "learning.readiness_assessed",
            {
                "model_id": model_id,
                "model_version": model.version,
                "previous_status": str(previous),
                "new_status": str(self.models.get(model_id).status),
                "observed": assessment.observed,
                "unobservable": assessment.unobservable,
                "mae": assessment.mae,
                "rmse": assessment.rmse,
                "context_buckets": assessment.context_buckets,
                "reasons": assessment.reasons,
            },
        )
        return assessment
