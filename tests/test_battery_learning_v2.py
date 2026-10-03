from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from ins_ei.learning_coordinator import LearningCoordinator


class H:
    def observation_summary(self, site):
        return {"duration_seconds": 7*3600, "signals": 3, "samples": 9, "first_observed_at": None, "last_observed_at": None, "coverage": {}}
    def numeric_series(self, site, component, point, limit=50000):
        base=datetime(2026,1,1,tzinfo=timezone.utc)
        def rows(vals): return [{"observed_at":(base+timedelta(minutes=i*5)).isoformat(),"value":v} for i,v in enumerate(vals)]
        data={
          "battery.soc": rows([50,51,52,52,51,50]),
          "battery.charge_power": rows([1000,1000,1000,0,0,0]),
          "battery.discharge_power": rows([0,0,0,0,1200,1200]),
        }
        return data.get(point,[])
    def save_model(self,*args,**kwargs): pass


class Models:
    def __init__(self):
        self.model=SimpleNamespace(metadata={},reason="",status=SimpleNamespace(value="LEARNING"))
    def get(self,id): return self.model


def test_battery_v2_segments_states_from_sitegraph_kind():
    c=LearningCoordinator("s",H(),Models(),SimpleNamespace())
    c.component_kinds={"huawei_wr1_battery":"BATTERY"}
    out=c.fit_battery_behavior_baseline()
    fit=out["fit"]["huawei_wr1_battery"]
    assert fit["states"]["CHARGING"]["samples"] == 3
    assert fit["states"]["DISCHARGING"]["samples"] == 2
    assert fit["states"]["IDLE"]["samples"] == 1
    assert fit["states"]["CHARGING"]["mean_soc_rate_pct_per_h"] > 0
    assert fit["states"]["DISCHARGING"]["mean_soc_rate_pct_per_h"] < 0
