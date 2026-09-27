from ins_ei.model_registry import LearningModelRecord, ModelDependency, ModelRegistry, ModelStatus
from ins_ei.readiness import OutcomeEvidence, ReadinessPolicy, assess_readiness


def test_model_becomes_ready_from_sufficient_good_evidence():
    evidence = [
        OutcomeEvidence("OBSERVED", residual=0.5, context_bucket=f"b{i % 3}")
        for i in range(30)
    ]
    result = assess_readiness(evidence, ReadinessPolicy(
        min_observed_outcomes=20,
        max_unobservable_fraction=0.2,
        max_mae=1.0,
        max_rmse=1.0,
        min_context_buckets=3,
    ))
    assert result.status == ModelStatus.READY


def test_model_stays_learning_when_coverage_is_too_small():
    evidence = [OutcomeEvidence("OBSERVED", residual=0.1, context_bucket="sunny") for _ in range(30)]
    result = assess_readiness(evidence, ReadinessPolicy(min_observed_outcomes=20, min_context_buckets=3))
    assert result.status == ModelStatus.LEARNING


def test_dependency_change_invalidates_only_affected_model():
    registry = ModelRegistry()
    registry.register(LearningModelRecord(
        id="battery_efficiency", version="1", capability="battery_optimization",
        dependencies=[ModelDependency("component", "battery")],
    ))
    registry.register(LearningModelRecord(
        id="building_heat", version="1", capability="heating",
        dependencies=[ModelDependency("component", "building")],
    ))
    affected = registry.invalidate_dependency("component", "battery", "battery replaced")
    assert affected == ["battery_efficiency"]
    assert registry.get("battery_efficiency").status == ModelStatus.INVALIDATED
    assert registry.get("building_heat").status == ModelStatus.LEARNING
