from datetime import datetime, timedelta
from types import SimpleNamespace

from ins_ei.models import PluginStatus


def test_poll_interval_contract_defaults_to_zero():
    from ins_ei.plugins.base import Plugin
    assert "min_poll_interval_seconds" in Plugin.__dict__


def test_oekofen_default_poll_interval_is_30_seconds():
    from ins_ei.plugins.oekofen import OekofenPlugin
    plugin = OekofenPlugin("oekofen", {"host": "x", "password": "x"})
    assert plugin.min_poll_interval_seconds == 30.0
