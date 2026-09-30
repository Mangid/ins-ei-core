from ins_ei.plugins.huawei_solar import HuaweiSolarPlugin


class FakeTransport:
    def string(self, unit, address, count):
        return {1: "SUN2000-10KTL-M1", 2: "SUN2000-10KTL-M1"}[unit]

    def read_registers(self, unit, address, count):
        values = {
            (1,32064,2): [0,5000], (1,32080,2): [0,4800],
            (2,32064,2): [0,4500], (2,32080,2): [0,4300],
            (1,37113,2): [0xFFFF,0xFC18],  # -1000 W = import
            (1,37758,2): [0,20000],       # 20 kWh
            (1,37760,1): [550],           # 55 %
            (1,37765,2): [0,1200],        # charging
        }
        return values[(unit,address,count)]

    @staticmethod
    def i32(regs):
        value=(regs[0]<<16)|regs[1]
        return value-0x100000000 if value&0x80000000 else value

    @staticmethod
    def u32(regs):
        return (regs[0]<<16)|regs[1]


def test_huawei_multi_inverter_aggregation_and_luna():
    p=HuaweiSolarPlugin("huawei_main",{"host":"x","inverter_unit_ids":"1,2","primary_unit_id":1})
    p.transport=FakeTransport();p.running=True
    points=p.read_points()
    values={(x.component_id,x.point):x.value for x in points}
    assert values[("pv","pv.generation_power")]==9500
    assert values[("grid_huawei","grid.import_power")]==1000
    assert values[("grid_huawei","grid.export_power")]==0
    assert values[("battery","battery.soc")]==55
    assert values[("battery","battery.charge_power")]==1200
    assert values[("battery","battery.capacity")]==20
    components={x["id"]:x["kind"] for x in p.discover_components(points)}
    assert components["huawei_inverter_1"]=="PV_INVERTER"
    assert components["huawei_inverter_2"]=="PV_INVERTER"
    assert components["battery"]=="BATTERY"
