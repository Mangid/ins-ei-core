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

    def dispatch_intent(
        self, intent: Intent, correlation_id: str | None = None
    ) -> CommandResult:
        correlation_id = correlation_id or self.runtime.last_correlation_id or self.runtime.historian.new_correlation_id()
        try:
            self.runtime.safety.assert_command_allowed()
        except Exception as exc:
            self.runtime.metrics.inc("command_blocked_emergency_stop_total")
            self.runtime.historian.record_command(
                self.runtime.site.site.id, correlation_id, intent.target,
                intent.command, intent.parameters, "BLOCKED",
                error=str(exc), context_version=self.runtime.context_version,
            )
            self.runtime.audit.record(
                "command.blocked",
                target=intent.target,
                command=intent.command,
                reason=str(exc),
            )
            raise
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
            self.runtime.audit.record(
                "command.attempt",
                target=intent.target,
                command=intent.command,
                plugin_instance=instance_id,
                parameters=intent.parameters,
            )
            result = managed.plugin.execute(intent.command, intent.parameters)
            self.runtime.historian.record_command(
                self.runtime.site.site.id, correlation_id, intent.target,
                intent.command, intent.parameters, "SUCCESS",
                plugin_instance=instance_id, result=result,
                context_version=self.runtime.context_version,
            )
            self.runtime.metrics.inc("command_success_total")
            self.runtime.audit.record(
                "command.success",
                target=intent.target,
                command=intent.command,
                plugin_instance=instance_id,
            )
            return CommandResult(
                target=intent.target,
                command=intent.command,
                plugin_instance=instance_id,
                success=True,
                result=result,
            )
        except Exception as exc:
            self.runtime.historian.record_command(
                self.runtime.site.site.id, correlation_id, intent.target,
                intent.command, intent.parameters, "FAILED",
                plugin_instance=instance_id, error=str(exc),
                context_version=self.runtime.context_version,
            )
            self.runtime.metrics.inc("command_failed_total")
            self.runtime.audit.record(
                "command.failed",
                target=intent.target,
                command=intent.command,
                plugin_instance=instance_id,
                error=str(exc),
            )
            return CommandResult(
                target=intent.target,
                command=intent.command,
                plugin_instance=instance_id,
                success=False,
                error=str(exc),
            )

    def dispatch(
        self, decision: Decision, correlation_id: str | None = None
    ) -> list[CommandResult]:
        correlation_id = correlation_id or self.runtime.last_correlation_id
        return [
            self.dispatch_intent(intent, correlation_id)
            for intent in decision.intents
        ]
