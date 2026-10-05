from __future__ import annotations
from datetime import datetime,timedelta
from .models import Quality
from .timeseries import TimeSlot

def _fixed_slots(series, value, timezone_now, hours=24):
    start=timezone_now.replace(minute=0,second=0,microsecond=0)
    return [TimeSlot(series=series,start=start+timedelta(hours=i),end=start+timedelta(hours=i+1),value=float(value),unit="ct/kWh",quality=Quality.GOOD,generated_at=timezone_now,source="SITE_TARIFF") for i in range(hours)]

def publish_site_tariffs(timeseries, tariff, now=None, hours=24):
    """Publish configured fixed prices. Dynamic providers populate the same canonical series later."""
    now=now or datetime.now().astimezone()
    result={}
    for side,series in (("import_config","market.import_price"),("export_config","market.export_price")):
        cfg=getattr(tariff,side,{}) or {}
        if str(cfg.get("type","")).lower()=="fixed" and cfg.get("price_ct_kwh") is not None:
            slots=_fixed_slots(series,cfg["price_ct_kwh"],now,hours)
            timeseries.replace(series,slots);result[series]=len(slots)
    return result
