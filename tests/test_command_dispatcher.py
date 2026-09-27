import pytest

from ins_ei.command_dispatcher import CommandDispatcher
from ins_ei.config import SiteConfig
from ins_ei.runtime import Runtime
from ins_ei.strategy import Intent


def test_dispatcher_rejects_command_not_declared_by_plugin():
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "test"},
        "plugin_instances": [
            {"id": "demo1", "plugin": "demo", "config": {"component_id": "heater"}}
        ],
        "components": [
            {"id": "heater", "kind": "POWER_TO_HEAT", "provider": "demo1"}
        ],
    })
    runtime = Runtime(site)
    runtime.configure()
    dispatcher = CommandDispatcher(runtime)

    with pytest.raises(ValueError, match="COMMAND_NOT_DECLARED"):
        dispatcher.dispatch_intent(
            Intent(target="heater", command="power_to_heat.set_power", parameters={"power_w": 1000})
        )
