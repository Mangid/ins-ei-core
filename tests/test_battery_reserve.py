from datetime import datetime

from ins_ei.config import SiteConfig
from ins_ei.models import Point, Quality, Source
from ins_ei.site_graph import SiteGraph
from ins_ei.state import StateStore
from ins_ei.strategy import StrategyContext, StrategyEngine
from ins_ei.strategies.battery_reserve import BatteryReserveStrategy


def ctx(soc=None):
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "battery-test"},
        "components": [{"id": "battery", "kind": "BATTERY"}],
    })
    state = StateStore()
    if soc is not None:
        state.ingest([Point(
            component_id="battery", point="battery.soc", value=float(soc), unit="%",
            quality=Quality.GOOD, observed_at=datetime.now().astimezone(),
            source=Source(plugin_instance="battery_io"),
        )])
    return StrategyContext(SiteGraph(site), state)


def test_reserve_blocks_at_minimum_soc():
    decision = StrategyEngine([BatteryReserveStrategy("battery", 20)]).evaluate(ctx(20))
    assert decision.action == "BLOCK_BATTERY_DISCHARGE"


def test_missing_soc_fails_safe():
    decision = StrategyEngine([BatteryReserveStrategy("battery", 20)]).evaluate(ctx())
    assert decision.action == "BLOCK_BATTERY_DISCHARGE"


def test_above_reserve_does_not_interfere():
    decision = StrategyEngine([BatteryReserveStrategy("battery", 20)]).evaluate(ctx(80))
    assert decision.action == "HOLD"
