from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ins_ei.runtime import Runtime
from ins_ei.strategy import Decision, Intent


@dataclass(frozen=True)
class CommandResult:
    target: str
    command: str
    plugin_instance: str
    success: bool
    result: Any = None
    error: str | None = None


class CommandDispatcher:
    """Validated bridge from canonical intents to device plugins."""

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    def dispatch_intent(self, intent: Intent) -> CommandResult:
        component = self.runtime.graph.component(intent.target)
        if not component.provider:
            raise ValueError(f"COMMAND_TARGET_HAS_NO_PROVIDER:{intent.target}")

        instance_id = component.provider
        plugin_id = self.runtime.instance_plugin_ids[instance_id]
        manifest = self.runtime.catalog.manifest(plugin_id)

        if intent.command not in manifest.commands:
            raise ValueError(
                f"COMMAND_NOT_DECLARED:{plugin_id}:{intent.command}"
            )

        managed = self.runtime.plugins[instance_id]
        try:
            result = managed.plugin.execute(intent.command, intent.parameters)
            return CommandResult(
                target=intent.target,
                command=intent.command,
                plugin_instance=instance_id,
                success=True,
                result=result,
            )
        except Exception as exc:
            return CommandResult(
                target=intent.target,
                command=intent.command,
                plugin_instance=instance_id,
                success=False,
                error=str(exc),
            )

    def dispatch(self, decision: Decision) -> list[CommandResult]:
        return [self.dispatch_intent(intent) for intent in decision.intents]
