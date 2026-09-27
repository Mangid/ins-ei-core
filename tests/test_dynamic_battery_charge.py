from datetime import datetime

from ins_ei.config import SiteConfig
from ins_ei.models import Point, Quality, Source
from ins_ei.site_graph import SiteGraph
from ins_ei.state import StateStore
from ins_ei.strategy import StrategyContext, StrategyEngine
from ins_ei.strategies.dynamic_battery_charge import DynamicBatteryChargeStrategy


def ctx(soc=40, price=12, limit=5000, price_quality=Quality.GOOD):
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "test"},
        "components": [
            {"id": "battery", "kind": "BATTERY"},
            {"id": "market", "kind": "MARKET"},
        ],
    })
    now = datetime.now().astimezone()
    state = StateStore()
    src = Source(plugin_instance="test")
    state.ingest([
        Point(component_id="battery", point="battery.soc", value=float(soc), unit="%", quality=Quality.GOOD, observed_at=now, source=src),
        Point(component_id="battery", point="battery.max_charge_power", value=float(limit), unit="W", quality=Quality.GOOD, observed_at=now, source=src),
        Point(component_id="market", point="market.import_price", value=float(price), unit="ct/kWh", quality=price_quality, observed_at=now, source=src),
    ])
    return StrategyContext(SiteGraph(site), state)


def strategy():
    return DynamicBatteryChargeStrategy(
        battery_component="battery",
        market_component="market",
        max_import_price_ct_kwh=15,
        target_soc_percent=80,
        max_charge_power_w=4000,
    )


def test_cheap_price_requests_grid_charge():
    decision = StrategyEngine([strategy()]).evaluate(ctx(soc=40, price=10, limit=5000))
    assert decision.action == "GRID_CHARGE_BATTERY"
    assert decision.intents[0].parameters["power_w"] == 4000


def test_device_limit_caps_charge():
    decision = StrategyEngine([strategy()]).evaluate(ctx(soc=40, price=10, limit=2500))
    assert decision.intents[0].parameters["power_w"] == 2500


def test_expensive_price_does_not_charge():
    assert StrategyEngine([strategy()]).evaluate(ctx(price=20)).action == "HOLD"


def test_target_soc_stops_grid_charge():
    assert StrategyEngine([strategy()]).evaluate(ctx(soc=80, price=10)).action == "HOLD"


def test_stale_price_fails_safe():
    assert StrategyEngine([strategy()]).evaluate(
        ctx(price=10, price_quality=Quality.STALE)
    ).action == "HOLD"
