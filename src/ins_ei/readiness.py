from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable

from ins_ei.model_registry import ModelStatus


@dataclass(frozen=True)
class OutcomeEvidence:
    status: str
    residual: float | None
    context_bucket: str | None = None


@dataclass(frozen=True)
class ReadinessPolicy:
    min_observed_outcomes: int = 20
    max_unobservable_fraction: float = 0.20
    max_mae: float | None = None
    max_rmse: float | None = None
    min_context_buckets: int = 1


@dataclass(frozen=True)
class ReadinessAssessment:
    status: ModelStatus
    observed: int
    unobservable: int
    unobservable_fraction: float
    mae: float | None
    rmse: float | None
    context_buckets: int
    reasons: tuple[str, ...]


def assess_readiness(
    evidence: Iterable[OutcomeEvidence],
    policy: ReadinessPolicy,
) -> ReadinessAssessment:
    samples = list(evidence)
    observed = [e for e in samples if e.status == "OBSERVED" and e.residual is not None]
    unobservable = [e for e in samples if e.status == "UNOBSERVABLE"]
    total = len(observed) + len(unobservable)
    fraction = len(unobservable) / total if total else 1.0

    residuals = [float(e.residual) for e in observed]
    mae = sum(abs(x) for x in residuals) / len(residuals) if residuals else None
    rmse = sqrt(sum(x * x for x in residuals) / len(residuals)) if residuals else None
    buckets = {e.context_bucket for e in observed if e.context_bucket is not None}

    reasons: list[str] = []
    if len(observed) < policy.min_observed_outcomes:
        reasons.append(f"observed {len(observed)} < required {policy.min_observed_outcomes}")
    if fraction > policy.max_unobservable_fraction:
        reasons.append(
            f"unobservable fraction {fraction:.3f} > allowed {policy.max_unobservable_fraction:.3f}"
        )
    if policy.max_mae is not None and (mae is None or mae > policy.max_mae):
        reasons.append(f"MAE {mae} exceeds {policy.max_mae}")
    if policy.max_rmse is not None and (rmse is None or rmse > policy.max_rmse):
        reasons.append(f"RMSE {rmse} exceeds {policy.max_rmse}")
    if len(buckets) < policy.min_context_buckets:
        reasons.append(f"context buckets {len(buckets)} < required {policy.min_context_buckets}")

    status = ModelStatus.READY if not reasons else ModelStatus.LEARNING
    return ReadinessAssessment(
        status=status,
        observed=len(observed),
        unobservable=len(unobservable),
        unobservable_fraction=fraction,
        mae=mae,
        rmse=rmse,
        context_buckets=len(buckets),
        reasons=tuple(reasons),
    )
