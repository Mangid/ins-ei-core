from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median
from zoneinfo import ZoneInfo

from .models import Quality
from .timeseries import TimeSlot


def _nearest(rows, ts, max_age_s=900):
    if not rows:
        return None
    best=min(rows,key=lambda r:abs((datetime.fromisoformat(r["observed_at"])-ts).total_seconds()))
    return best["value"] if abs((datetime.fromisoformat(best["observed_at"])-ts).total_seconds())<=max_age_s else None


def base_load_profile_v4(historian, site_id: str, component_kinds: dict[str,str], timezone: str, hours: int=24):
    """Port of INS_EI_BASE_LOAD_PROFILE_V4 using local canonical historian data."""
    tz=ZoneInfo(timezone); now=datetime.now(tz); hours=max(1,min(int(hours),48))
    grids=[c for c,k in component_kinds.items() if k=="GRID"]
    pvs=[c for c,k in component_kinds.items() if k=="PV"]
    bats=[c for c,k in component_kinds.items() if k=="BATTERY"]
    p2hs=[c for c,k in component_kinds.items() if k=="POWER_TO_HEAT"]
    if not grids: return {"model":"INS_EI_BASE_LOAD_PROFILE_V4","quality":"LEARNING","slots":[]}
    grid=historian.numeric_series(site_id,grids[0],"grid.import_power",50000)
    pv=[historian.numeric_series(site_id,c,"pv.generation_power",50000) for c in pvs]
    charge=[historian.numeric_series(site_id,c,"battery.charge_power",50000) for c in bats]
    discharge=[historian.numeric_series(site_id,c,"battery.discharge_power",50000) for c in bats]
    p2h=[historian.numeric_series(site_id,c,"power.electrical",50000) for c in p2hs]
    buckets={}; days=set(); rejected=0
    for row in grid:
        ts=datetime.fromisoformat(row["observed_at"]).astimezone(tz)
        pv_w=sum(_nearest(x,ts) or 0 for x in pv); ch=sum(_nearest(x,ts) or 0 for x in charge)
        dis=sum(_nearest(x,ts) or 0 for x in discharge); ctrl=sum(_nearest(x,ts) or 0 for x in p2h)
        total=max(0.0,pv_w+row["value"]+dis-ch); base=max(0.0,total-max(0.0,ctrl))
        if base>5000: rejected+=1; continue
        buckets.setdefault((ts.weekday(),ts.hour),[]).append(base);days.add(ts.date())
    allv=[v for xs in buckets.values() for v in xs if v>0]; global_med=median(allv) if allv else 500.0
    slots=[]
    for n in range(hours):
        start=now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=n)
        vals=[v for v in buckets.get((start.weekday(),start.hour),[]) if v>0]
        source="PROFILE"
        if len(vals)<4: vals=[v for (wd,h),xs in buckets.items() if h==start.hour for v in xs if v>0]
        if vals: watts=median(vals); quality="GOOD" if len(vals)>=8 else "LEARNING"
        else:
            neigh=[v for d in (-2,-1,1,2) for (wd,h),xs in buckets.items() if h==(start.hour+d)%24 for v in xs if v>0]
            watts=median(neigh) if neigh else global_med; source="NEIGHBOUR_FALLBACK" if neigh else "GLOBAL_FALLBACK";quality="FALLBACK"
        slots.append({"start":start,"kwh":max(100.0,watts)/1000.0,"samples":len(vals),"quality":quality,"source":source})
    learned=len(days); q="GOOD" if learned>=21 else ("MEDIUM" if learned>=7 else "LEARNING")
    return {"model":"INS_EI_BASE_LOAD_PROFILE_V4","quality":q,"learned_days":learned,"rejected_points":rejected,"total_kwh":sum(x["kwh"] for x in slots),"slots":slots}


def pv_profile_v2(historian, site_id: str, component_kinds: dict[str,str], timezone: str, hours: int=24):
    """Port of learned PV profile V2. Weather attenuation is added by forecast inputs later."""
    tz=ZoneInfo(timezone);now=datetime.now(tz);hours=max(1,min(int(hours),48))
    pvs=[c for c,k in component_kinds.items() if k=="PV"]
    by_hour={};days=set()
    # Sum logical PV components per timestamp approximately; use all observations to learn real site geometry.
    for c in pvs:
        for row in historian.numeric_series(site_id,c,"pv.generation_power",50000):
            ts=datetime.fromisoformat(row["observed_at"]).astimezone(tz)
            by_hour.setdefault(ts.hour,[]).append(max(0.0,row["value"]));days.add(ts.date())
    slots=[]
    for n in range(hours):
        start=now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=n);vals=by_hour.get(start.hour,[])
        watts=median(vals) if vals else 0.0
        if watts<50: watts=0.0
        slots.append({"start":start,"kwh":watts/1000.0,"baseline_kwh":watts/1000.0,"samples":len(vals),"quality":"GOOD" if len(vals)>=12 and len(days)>=7 else "LEARNING","source":"HISTORICAL_PV_PROFILE"})
    learned=len(days);q="GOOD" if learned>=21 else ("MEDIUM" if learned>=7 else "LEARNING")
    return {"model":"INS_EI_PV_PROFILE_V2","quality":q,"learned_days":learned,"weather_used":False,"total_kwh":sum(x["kwh"] for x in slots),"slots":slots}


def publish_forecast(timeseries, consumption: dict, pv: dict):
    now=datetime.now().astimezone()
    for name,data in (("forecast.consumption_energy",consumption),("forecast.pv_energy",pv)):
        slots=[TimeSlot(series=name,start=x["start"],end=x["start"]+timedelta(hours=1),value=round(x["kwh"],3),unit="kWh",quality=Quality.GOOD,generated_at=now,source=data["model"],metadata={"quality":x["quality"],"samples":x["samples"],"source":x["source"]}) for x in data["slots"]]
        timeseries.replace(name,slots)
