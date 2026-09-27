from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from ins_ei.models import Quality
from ins_ei.state import StateStore


@dataclass(frozen=True)
class OutcomeExpectation:
    correlation_id: str
    metric_component: str
    metric_point: str
    horizon_seconds: int
    expected_delta: float | None = None
    expected_value: float | None = None
    tolerance: float | None = None
    unit: str | None = None
    model_id: str | None = None
    model_version: str | None = None


@dataclass
class PendingOutcome:
    expectation: OutcomeExpectation
    created_at: datetime
    due_at: datetime
    baseline_value: float | None
    baseline_quality: Quality | None


@dataclass(frozen=True)
class OutcomeResult:
    correlation_id: str
    status: str
    metric_component: str
    metric_point: str
    expected_value: float | None
    actual_value: float | None
    residual: float | None
    absolute_error: float | None
    within_tolerance: bool | None
    observed_at: datetime
    model_id: str | None
    model_version: str | None
    reason: str | None = None


class OutcomeTracker:
    def __init__(self, state: StateStore, historian, site_id: str, context_version: str | None = None) -> None:
        self.state = state
        self.historian = historian
        self.site_id = site_id
        self.context_version = context_version
        self.pending: dict[str, PendingOutcome] = {}

    def register(self, expectation: OutcomeExpectation, now: datetime | None = None) -> PendingOutcome:
        now = now or datetime.now().astimezone()
        point = self.state.get(expectation.metric_component, expectation.metric_point, now)
        baseline = None
        quality = None
        if point is not None:
            quality = point.quality
            if point.quality == Quality.GOOD:
                baseline = float(point.value)

        if expectation.expected_delta is not None and expectation.expected_value is not None:
            raise ValueError("OUTCOME_EXPECTATION_AMBIGUOUS")
        if expectation.expected_delta is None and expectation.expected_value is None:
            raise ValueError("OUTCOME_EXPECTATION_MISSING_TARGET")
        if expectation.expected_delta is not None and baseline is None:
            raise ValueError("OUTCOME_BASELINE_UNAVAILABLE")

        pending = PendingOutcome(
            expectation=expectation,
            created_at=now,
            due_at=now + timedelta(seconds=expectation.horizon_seconds),
            baseline_value=baseline,
            baseline_quality=quality,
        )
        self.pending[expectation.correlation_id] = pending
        self.historian.record_event(
            self.site_id,
            "outcome.expected",
            {
                "metric_component": expectation.metric_component,
                "metric_point": expectation.metric_point,
                "horizon_seconds": expectation.horizon_seconds,
                "expected_delta": expectation.expected_delta,
                "expected_value": expectation.expected_value,
                "baseline_value": baseline,
                "unit": expectation.unit,
                "model_id": expectation.model_id,
                "model_version": expectation.model_version,
            },
            correlation_id=expectation.correlation_id,
            context_version=self.context_version,
        )
        return pending

    def evaluate_due(self, now: datetime | None = None) -> list[OutcomeResult]:
        now = now or datetime.now().astimezone()
        results: list[OutcomeResult] = []
        for correlation_id, pending in list(self.pending.items()):
            if now < pending.due_at:
                continue
            result = self._evaluate(pending, now)
            results.append(result)
            del self.pending[correlation_id]
            self.historian.record_event(
                self.site_id,
                "outcome.observed",
                {
                    "status": result.status,
                    "metric_component": result.metric_component,
                    "metric_point": result.metric_point,
                    "expected_value": result.expected_value,
                    "actual_value": result.actual_value,
                    "residual": result.residual,
                    "absolute_error": result.absolute_error,
                    "within_tolerance": result.within_tolerance,
                    "model_id": result.model_id,
                    "model_version": result.model_version,
                    "reason": result.reason,
                },
                correlation_id=correlation_id,
                context_version=self.context_version,
            )
        return results

    def _evaluate(self, pending: PendingOutcome, now: datetime) -> OutcomeResult:
        exp = pending.expectation
        point = self.state.get(exp.metric_component, exp.metric_point, now)
        if point is None or point.quality != Quality.GOOD:
            return OutcomeResult(
                correlation_id=exp.correlation_id,
                status="UNOBSERVABLE",
                metric_component=exp.metric_component,
                metric_point=exp.metric_point,
                expected_value=None,
                actual_value=None,
                residual=None,
                absolute_error=None,
                within_tolerance=None,
                observed_at=now,
                model_id=exp.model_id,
                model_version=exp.model_version,
                reason="Outcome point missing, stale or not GOOD.",
            )

        actual = float(point.value)
        expected = (
            float(exp.expected_value)
            if exp.expected_value is not None
            else float(pending.baseline_value) + float(exp.expected_delta)
        )
        residual = actual - expected
        absolute_error = abs(residual)
        within = None if exp.tolerance is None else absolute_error <= exp.tolerance

        return OutcomeResult(
            correlation_id=exp.correlation_id,
            status="OBSERVED",
            metric_component=exp.metric_component,
            metric_point=exp.metric_point,
            expected_value=expected,
            actual_value=actual,
            residual=residual,
            absolute_error=absolute_error,
            within_tolerance=within,
            observed_at=now,
            model_id=exp.model_id,
            model_version=exp.model_version,
        )
