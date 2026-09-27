from types import SimpleNamespace

from ins_ei.autonomy import AutonomyGate, AutonomyMode, CapabilityAutonomy
from ins_ei.historian import Historian
from ins_ei.learning_coordinator import LearningCoordinator
from ins_ei.model_registry import LearningModelRecord, ModelRegistry, ModelStatus
from ins_ei.readiness import ReadinessPolicy


def test_outcomes_promote_model_and_persist_across_restart(tmp_path):
    historian = Historian(tmp_path / "h.db")
    models = ModelRegistry()
    autonomy = AutonomyGate(models)
    coordinator = LearningCoordinator("site", historian, models, autonomy)
    coordinator.register_model(
        LearningModelRecord(id="buffer", version="1", capability="thermal_optimization"),
        ReadinessPolicy(min_observed_outcomes=2, max_mae=1.0),
    )
    for i, residual in enumerate((0.5, -0.5)):
        coordinator.ingest_outcome(SimpleNamespace(
            model_id="buffer", model_version="1", correlation_id=str(i),
            status="OBSERVED", residual=residual,
        ))
    assert models.get("buffer").status == ModelStatus.READY

    restored_models = ModelRegistry()
    restored = LearningCoordinator(
        "site", historian, restored_models, AutonomyGate(restored_models)
    )
    restored.restore()
    assert restored_models.get("buffer").status == ModelStatus.READY


def test_ready_model_degradation_drops_autonomy_to_shadow(tmp_path):
    historian = Historian(tmp_path / "h.db")
    models = ModelRegistry()
    autonomy = AutonomyGate(models)
    coordinator = LearningCoordinator("site", historian, models, autonomy)
    coordinator.register_model(
        LearningModelRecord(id="battery", version="1", capability="battery_optimization"),
        ReadinessPolicy(min_observed_outcomes=1, max_mae=1.0),
    )
    coordinator.ingest_outcome(SimpleNamespace(
        model_id="battery", model_version="1", correlation_id="good",
        status="OBSERVED", residual=0.1,
    ))
    autonomy.configure(CapabilityAutonomy(
        capability="battery_optimization", mode=AutonomyMode.AUTONOMOUS,
        required_models=["battery"], physical_write_allowed=True,
    ))
    coordinator.ingest_outcome(SimpleNamespace(
        model_id="battery", model_version="1", correlation_id="bad",
        status="OBSERVED", residual=10.0,
    ))
    assert models.get("battery").status == ModelStatus.DEGRADED
    assert autonomy.get("battery_optimization").mode == AutonomyMode.SHADOW
