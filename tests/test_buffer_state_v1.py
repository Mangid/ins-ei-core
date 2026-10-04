from datetime import datetime, timezone
from types import SimpleNamespace
from ins_ei.learning_coordinator import LearningCoordinator

class H:
    def observation_summary(self, site):
        return {"duration_seconds": 7*3600,"signals":2,"samples":4,"first_observed_at":None,"last_observed_at":None,"coverage":{}}
    def numeric_series(self, site, component, point, limit=20000):
        if component=="buffer" and point=="thermal.temperature_upper":
            return [{"observed_at":datetime.now(timezone.utc).isoformat(),"value":60.0}]
        if component=="buffer" and point=="thermal.temperature_lower":
            return [{"observed_at":datetime.now(timezone.utc).isoformat(),"value":41.0}]
        return []
    def save_model(self,*args,**kwargs): pass
class M:
    def __init__(self): self.m=SimpleNamespace(metadata={},reason="")
    def get(self,id): return self.m

def test_buffer_state_v1_reports_partial_observability_and_topology():
    c=LearningCoordinator("kaufmann",H(),M(),SimpleNamespace())
    c.component_kinds={"buffer":"BUFFER","pellet_boiler":"HEAT_GENERATOR","power_to_heat":"POWER_TO_HEAT","hk1":"HEATING_CIRCUIT","dhw":"DHW"}
    c.component_properties={"buffer":{"volume_l":600,"temperature_sensor_positions":{"TOP":"thermal.temperature_upper","UPPER_MIDDLE":"thermal.temperature_lower"}}}
    c.site_relations=[
      {"from":"pellet_boiler","to":"buffer","type":"HEATS"},
      {"from":"power_to_heat","to":"buffer","type":"HEATS"},
      {"from":"buffer","to":"hk1","type":"SUPPLIES"},
      {"from":"buffer","to":"dhw","type":"HEATS"},
    ]
    fit=c.fit_buffer_state_v1()["buffers"]["buffer"]
    assert fit["observability"]=="PARTIAL"
    assert fit["coverage_fraction"]==0.5
    assert fit["observed_positions"]==["TOP","UPPER_MIDDLE"]
    assert {x["component"] for x in fit["incoming"]}=={"pellet_boiler","power_to_heat"}
    assert {x["component"] for x in fit["outgoing"]}=={"hk1","dhw"}
    assert fit["energy_content_claimed"] is False
