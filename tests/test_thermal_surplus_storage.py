from datetime import datetime

from ins_ei.config import SiteConfig
from ins_ei.models import Point, Quality, Source
from ins_ei.site_graph import SiteGraph
from ins_ei.state import StateStore
from ins_ei.strategy import StrategyContext, StrategyEngine
from ins_ei.strategies.thermal_surplus_storage import ThermalSurplusStorageStrategy


def make_context(export_w=3500, buffer_c=55, export_quality=Quality.GOOD):
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "test"},
        "plugin_instances": [
            {"id": "meter", "plugin": "shrdzm", "config": {}},
            {"id": "heater_io", "plugin": "mypv", "config": {}},
        ],
        "components": [
            {"id": "grid", "kind": "GRID", "provider": "meter"},
            {"id": "buffer", "kind": "BUFFER"},
            {"id": "heater", "kind": "POWER_TO_HEAT", "provider": "heater_io"},
        ],
        "relations": [
            {"from": "grid", "to": "heater", "type": "SUPPLIES"},
            {"from": "heater", "to": "buffer", "type": "HEATS"},
        ],
    })
    now = datetime.now().astimezone()
    state = StateStore()
    state.ingest([
        Point(component_id="grid", point="grid.export_power", value=export_w, unit="W",
              quality=export_quality, observed_at=now, source=Source(plugin_instance="meter")),
        Point(component_id="buffer", point="thermal.temperature_upper", value=buffer_c, unit="°C",
              quality=Quality.GOOD, observed_at=now, source=Source(plugin_instance="sensor")),
    ])
    return StrategyContext(SiteGraph(site), state)


def strategy():
    return ThermalSurplusStorageStrategy(
        grid_component="grid",
        storage_component="buffer",
        temperature_point="thermal.temperature_upper",
        max_temperature_c=75,
        power_to_heat_component="heater",
        max_power_w=9000,
        reserve_export_w=100,
        minimum_power_w=100,
    )


def test_surplus_is_converted_to_power_to_heat_request():
    decision = StrategyEngine([strategy()]).evaluate(make_context(export_w=3500, buffer_c=55))
    assert decision.action == "STORE_ELECTRICAL_SURPLUS_AS_HEAT"
    assert decision.intents[0].command == "power_to_heat.set_power"
    assert decision.intents[0].parameters["power_w"] == 3400


def test_hot_storage_blocks_surplus_heating():
    decision = StrategyEngine([strategy()]).evaluate(make_context(export_w=5000, buffer_c=75))
    assert decision.action == "HOLD"


def test_bad_grid_data_blocks_new_heating_action():
    decision = StrategyEngine([strategy()]).evaluate(
        make_context(export_w=5000, buffer_c=50, export_quality=Quality.STALE)
    )
    assert decision.action == "HOLD"


def test_requested_power_is_capped():
    decision = StrategyEngine([strategy()]).evaluate(make_context(export_w=12000, buffer_c=50))
    assert decision.intents[0].parameters["power_w"] == 9000
