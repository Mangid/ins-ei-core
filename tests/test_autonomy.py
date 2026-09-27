from ins_ei.autonomy import AutonomyGate, AutonomyMode, CapabilityAutonomy
from ins_ei.model_registry import LearningModelRecord, ModelRegistry, ModelStatus


def test_autonomous_capability_requires_ready_models_and_write_permission():
    models = ModelRegistry()
    models.register(LearningModelRecord(
        id="battery_efficiency", version="1", capability="battery_optimization",
        status=ModelStatus.READY,
    ))
    gate = AutonomyGate(models)
    gate.configure(CapabilityAutonomy(
        capability="battery_optimization",
        mode=AutonomyMode.AUTONOMOUS,
        required_models=["battery_efficiency"],
        physical_write_allowed=True,
    ))
    assert gate.assess("battery_optimization").allowed is True


def test_shadow_never_executes_physical_command():
    gate = AutonomyGate(ModelRegistry())
    gate.configure(CapabilityAutonomy(
        capability="thermal_optimization",
        mode=AutonomyMode.SHADOW,
        physical_write_allowed=True,
    ))
    assert gate.assess("thermal_optimization").allowed is False


def test_model_regression_can_drop_autonomy_to_shadow():
    models = ModelRegistry()
    models.register(LearningModelRecord(
        id="buffer_model", version="1", capability="thermal_optimization",
        status=ModelStatus.READY,
    ))
    gate = AutonomyGate(models)
    gate.configure(CapabilityAutonomy(
        capability="thermal_optimization",
        mode=AutonomyMode.AUTONOMOUS,
        required_models=["buffer_model"],
        physical_write_allowed=True,
    ))
    affected = gate.degrade_for_model("buffer_model", "prediction error increased")
    assert affected == ["thermal_optimization"]
    assert gate.get("thermal_optimization").mode == AutonomyMode.SHADOW
