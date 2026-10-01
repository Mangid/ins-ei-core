import asyncio
from types import SimpleNamespace

import ins_ei.plugins.huawei_solar as mod
from ins_ei.plugins.huawei_solar import HuaweiSolarPlugin


class FakeClient:
    unit_id = 1
    async def connect(self): pass
    async def disconnect(self): pass
    async def get(self, key):
        values = {
            mod.rn.INPUT_POWER: 5000,
            mod.rn.ACTIVE_POWER: 4800,
            mod.rn.POWER_METER_ACTIVE_POWER: 1000,
            mod.rn.STORAGE_STATE_OF_CAPACITY: 55,
            mod.rn.STORAGE_CHARGE_DISCHARGE_POWER: 1200,
        }
        return SimpleNamespace(value=values[key])


class FakeSubClient(FakeClient):
    unit_id = 2
    async def get(self, key):
        values={mod.rn.INPUT_POWER:4500,mod.rn.ACTIVE_POWER:4300}
        return SimpleNamespace(value=values[key])


class FakeDevice:
    def __init__(self, client, model): self.client=client; self.model_name=model


def test_huawei_multi_inverter_aggregation_and_luna(monkeypatch):
    client=FakeClient()
    monkeypatch.setattr(mod,"create_tcp_client",lambda **kwargs: client)
    async def primary(c): return FakeDevice(c,"SUN2000-10KTL-M1")
    async def sub(device,unit): return FakeDevice(FakeSubClient(),"SUN2000-10KTL-M1")
    monkeypatch.setattr(mod,"create_device_instance",primary)
    monkeypatch.setattr(mod,"create_sub_device_instance",sub)

    p=HuaweiSolarPlugin("huawei_main",{"host":"x","inverter_unit_ids":"1,2","primary_unit_id":1,"component_prefix":"huawei_a"})
    p.running=True
    points=p.read_points()
    values={(x.component_id,x.point):x.value for x in points}
    assert values[("huawei_a_pv","pv.generation_power")]==9500
    assert values[("huawei_a_grid","grid.import_power")]==1000
    assert values[("huawei_a_grid","grid.export_power")]==0
    assert values[("huawei_a_battery","battery.soc")]==55
    assert values[("huawei_a_battery","battery.charge_power")]==1200
    components={x["id"]:x["kind"] for x in p.discover_components(points)}
    assert components["huawei_a_inverter_1"]=="PV_INVERTER"
    assert components["huawei_a_inverter_2"]=="PV_INVERTER"
    assert components["huawei_a_battery"]=="BATTERY"


def test_secondary_host_can_skip_meter_and_battery(monkeypatch):
    client=FakeClient()
    monkeypatch.setattr(mod,"create_tcp_client",lambda **kwargs: client)
    async def primary(c): return FakeDevice(c,"SUN2000-10KTL-M1")
    monkeypatch.setattr(mod,"create_device_instance",primary)
    p=HuaweiSolarPlugin("huawei_wr2",{"host":"x","inverter_unit_ids":"2","primary_unit_id":2,"component_prefix":"huawei_wr2","include_meter":"false","include_battery":"false"})
    p.running=True
    points=p.read_points()
    ids={x.component_id for x in points}
    assert "huawei_wr2_pv" in ids
    assert "huawei_wr2_inverter_1" in ids
    assert "huawei_wr2_grid" not in ids
    assert "huawei_wr2_battery" not in ids
