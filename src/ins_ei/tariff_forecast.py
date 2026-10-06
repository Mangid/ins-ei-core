from __future__ import annotations
from datetime import datetime,timedelta
import json
from urllib.request import Request,urlopen
from .models import Quality
from .timeseries import TimeSlot

def _fixed_slots(series, value, timezone_now, hours=24):
    start=timezone_now.replace(minute=0,second=0,microsecond=0)
    return [TimeSlot(series=series,start=start+timedelta(hours=i),end=start+timedelta(hours=i+1),value=float(value),unit="ct/kWh",quality=Quality.GOOD,generated_at=timezone_now,source="SITE_TARIFF") for i in range(hours)]

def publish_site_tariffs(timeseries, tariff, now=None, hours=24):
    """Publish configured fixed prices. Dynamic providers populate the same canonical series later."""
    now=now or datetime.now().astimezone()
    dynamic=publish_awattar_dynamic(timeseries,tariff,now)
    result=dict(dynamic)
    for side,series in (("import_config","market.import_price"),("export_config","market.export_price")):
        cfg=getattr(tariff,side,{}) or {}
        if str(cfg.get("type","")).lower()=="fixed" and cfg.get("price_ct_kwh") is not None:
            slots=_fixed_slots(series,cfg["price_ct_kwh"],now,hours)
            timeseries.replace(series,slots);result[series]=len(slots)
    return result


def _awattar_market():
    with urlopen(Request("https://api.awattar.at/v1/marketdata",headers={"User-Agent":"INS-EI-Core/1.0"}),timeout=10) as r:
        return json.loads(r.read().decode()).get("data",[])

def publish_awattar_dynamic(timeseries, tariff, now=None):
    now=now or datetime.now().astimezone()
    imp=getattr(tariff,"import_config",{}) or {};exp=getattr(tariff,"export_config",{}) or {}
    if str(imp.get("provider","")).lower()!="awattar" and str(exp.get("provider","")).lower()!="awattar": return {}
    data=_awattar_market();imports=[];exports=[]
    for x in data:
        start=datetime.fromtimestamp(x["start_timestamp"]/1000,now.tzinfo);end=datetime.fromtimestamp(x["end_timestamp"]/1000,now.tzinfo)
        epex=float(x["marketprice"])/10.0 # EUR/MWh -> ct/kWh
        if str(imp.get("type","")).lower()=="dynamic":
            surcharge=float(imp.get("surcharge_ct_kwh",1.5));vat=float(imp.get("vat_percent",20))
            value=(epex+surcharge)*(1+vat/100)
            imports.append(TimeSlot(series="market.import_price",start=start,end=end,value=value,unit="ct/kWh",quality=Quality.GOOD,generated_at=now,source="AWATTAR_EPEX_AT"))
        if str(exp.get("type","")).lower()=="dynamic":
            fee=float(exp.get("absolute_fee_percent",19))
            value=epex-(abs(epex)*fee/100)
            exports.append(TimeSlot(series="market.export_price",start=start,end=end,value=value,unit="ct/kWh",quality=Quality.GOOD,generated_at=now,source="AWATTAR_SUNNY_SPOT"))
    if imports:timeseries.replace("market.import_price",imports)
    if exports:timeseries.replace("market.export_price",exports)
    return {"import_slots":len(imports),"export_slots":len(exports),"source":"aWATTar API"}
