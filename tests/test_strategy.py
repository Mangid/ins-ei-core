from datetime import datetime

from ins_ei.config import SiteConfig
from ins_ei.models import Point, Quality, Source
from ins_ei.site_graph import SiteGraph
from ins_ei.state import StateStore
from ins_ei.strategy import Priority, StrategyContext, StrategyEngine
from ins_ei.strategies import DhwMinimumStrategy


def context_with_dhw(temp: float):
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "test"},
        "plugin_instances": [{"id": "boiler_io", "plugin": "oekofen", "config": {}}],
        "components": [
            {"id": "boiler", "kind": "HEAT_GENERATOR", "provider": "boiler_io"},
            {"id": "dhw", "kind": "DHW", "provider": "boiler_io"},
        ],
        "relations": [{"from": "boiler", "to": "dhw", "type": "HEATS"}],
    })
    state = StateStore()
    state.ingest([Point(
        component_id="dhw",
        point="thermal.temperature",
        value=temp,
        unit="°C",
        quality=Quality.GOOD,
        observed_at=datetime.now().astimezone(),
        source=Source(plugin_instance="boiler_io"),
    )])
    return StrategyContext(SiteGraph(site), state)


def test_dhw_minimum_requests_canonical_heat_once():
    engine = StrategyEngine([
        DhwMinimumStrategy(
            dhw_component="dhw",
            temperature_point="thermal.temperature",
            minimum_c=50,
            heat_source="boiler",
        )
    ])
    decision = engine.evaluate(context_with_dhw(47))
    assert decision.action == "REQUEST_DHW_HEAT"
    assert decision.priority == Priority.MANDATORY
    assert decision.intents[0].command == "dhw.request_once"
    assert decision.intents[0].target == "boiler"


def test_dhw_above_minimum_falls_back_to_hold():
    engine = StrategyEngine([
        DhwMinimumStrategy("dhw", "thermal.temperature", 50, "boiler")
    ])
    decision = engine.evaluate(context_with_dhw(55))
    assert decision.action == "HOLD"
    assert decision.winning_strategy == "hold"
