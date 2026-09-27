from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ins_ei.model_registry import ModelRegistry, ModelStatus


class AutonomyMode(StrEnum):
    LEARNING = "LEARNING"
    SHADOW = "SHADOW"
    ASSISTED = "ASSISTED"
    AUTONOMOUS = "AUTONOMOUS"


@dataclass
class CapabilityAutonomy:
    capability: str
    mode: AutonomyMode = AutonomyMode.LEARNING
    required_models: list[str] = field(default_factory=list)
    physical_write_allowed: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class AutonomyDecision:
    allowed: bool
    capability: str
    mode: AutonomyMode
    reason: str


class AutonomyGate:
    """Capability-specific permission gate for physical execution."""

    def __init__(self, models: ModelRegistry) -> None:
        self.models = models
        self._capabilities: dict[str, CapabilityAutonomy] = {}

    def configure(self, config: CapabilityAutonomy) -> None:
        self._capabilities[config.capability] = config

    def get(self, capability: str) -> CapabilityAutonomy:
        return self._capabilities.get(
            capability,
            CapabilityAutonomy(
                capability=capability,
                mode=AutonomyMode.LEARNING,
                physical_write_allowed=False,
                reason="capability not configured",
            ),
        )

    def assess(self, capability: str) -> AutonomyDecision:
        config = self.get(capability)

        if config.mode != AutonomyMode.AUTONOMOUS:
            return AutonomyDecision(
                False, capability, config.mode,
                f"Capability is {config.mode}; autonomous physical execution is disabled.",
            )

        if not config.physical_write_allowed:
            return AutonomyDecision(
                False, capability, config.mode,
                "Physical write permission is not enabled for this capability.",
            )

        for model_id in config.required_models:
            model = self.models.get(model_id)
            if model.status != ModelStatus.READY:
                return AutonomyDecision(
                    False, capability, config.mode,
                    f"Required model {model_id} is {model.status}, not READY.",
                )

        return AutonomyDecision(
            True, capability, config.mode,
            "Capability is AUTONOMOUS, writes are permitted and required models are READY.",
        )

    def degrade_for_model(self, model_id: str, reason: str) -> list[str]:
        affected = []
        for capability, config in self._capabilities.items():
            if model_id in config.required_models and config.mode == AutonomyMode.AUTONOMOUS:
                config.mode = AutonomyMode.SHADOW
                config.reason = reason
                affected.append(capability)
        return affected

    def snapshot(self) -> list[CapabilityAutonomy]:
        return list(self._capabilities.values())


COMMAND_CAPABILITY_PREFIXES = {
    "battery.": "battery_optimization",
    "power_to_heat.": "thermal_optimization",
    "dhw.": "dhw_control",
    "heat_generator.": "heating_control",
}


def capability_for_command(command: str) -> str:
    for prefix, capability in COMMAND_CAPABILITY_PREFIXES.items():
        if command.startswith(prefix):
            return capability
    return f"command:{command}"
