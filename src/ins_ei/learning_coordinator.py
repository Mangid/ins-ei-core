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
