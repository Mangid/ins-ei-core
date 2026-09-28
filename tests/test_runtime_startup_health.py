from datetime import datetime

from ins_ei.models import PluginStatus
from ins_ei.runtime import ManagedPlugin


def test_managed_plugin_can_be_starting_without_degraded_error():
    managed = ManagedPlugin(plugin=object())
    managed.status = PluginStatus.STARTING
    managed.started_at = datetime.now().astimezone()
    managed.error = None
    assert managed.status == PluginStatus.STARTING
    assert managed.error is None
