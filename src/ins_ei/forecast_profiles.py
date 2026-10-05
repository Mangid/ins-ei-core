from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median
from zoneinfo import ZoneInfo
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import Quality
from .timeseries import TimeSlot


def _nearest(rows, ts, max_age_s=900):
    if not rows:
        return None
    best=min(rows,key=lambda r:abs((datetime.fromisoformat(r["observed_at"])-ts).total_seconds()))
    return best["value"] if abs((datetime.fromisoformat(best["observed_at"])-ts).total_seconds())<=max_age_s else None


def _balance_components(component_kinds, component_properties, kind, role):
    candidates=[c for c,k in component_kinds.items() if k==kind]
    explicit=[c for c in candidates if (component_properties.get(c,{}) or {}).get('forecast_role')==role]
    if explicit:return explicit
    return candidates if len(candidates)<=1 else []


def base_load_profile_v4(historian, site_id: str, component_kinds: dict[str,str], timezone: str, hours: int=24, component_properties=None):
    """Port of INS_EI_BASE_LOAD_PROFILE_V4 using local canonical historian data."""
    tz=ZoneInfo(timezone); now=datetime.now(tz); hours=max(1,min(int(hours),48))
    component_properties=component_properties or {}
    grids=_balance_components(component_kinds,component_properties,"GRID","BALANCE_GRID")
    pvs=_balance_components(component_kinds,component_properties,"PV","BALANCE_PV")
    bats=_balance_components(component_kinds,component_properties,"BATTERY","BALANCE_BATTERY")
    p2hs=[c for c,k in component_kinds.items() if k=="POWER_TO_HEAT"]
    if not grids: return {"model":"INS_EI_BASE_LOAD_PROFILE_V4","quality":"LEARNING","slots":[]}

    def bucket(rows):
        out={}
        for r in rows:
            ts=datetime.fromisoformat(r["observed_at"]).astimezone(tz)
            key=ts.replace(second=0,microsecond=0)
            out.setdefault(key,[]).append(float(r["value"]))
        return {k:sum(v)/len(v) for k,v in out.items()}

    grid_import=bucket(historian.numeric_series(site_id,grids[0],"grid.import_power",50000))
    grid_export=bucket(historian.numeric_series(site_id,grids[0],"grid.export_power",50000))
    pv_maps=[bucket(historian.numeric_series(site_id,c,"pv.generation_power",50000)) for c in pvs]
    ch_maps=[bucket(historian.numeric_series(site_id,c,"battery.charge_power",50000)) for c in bats]
    dis_maps=[bucket(historian.numeric_series(site_id,c,"battery.discharge_power",50000)) for c in bats]
    p2h_maps=[bucket(historian.numeric_series(site_id,c,"power.electrical",50000)) for c in p2hs]
    keys=sorted(grid_import)
    buckets={};days=set();rejected=0
    for key in keys:
        pv_w=sum(x.get(key,0.0) for x in pv_maps)
        net_grid=grid_import.get(key,0.0)-grid_export.get(key,0.0)
        ch=sum(x.get(key,0.0) for x in ch_maps);dis=sum(x.get(key,0.0) for x in dis_maps)
        ctrl=sum(x.get(key,0.0) for x in p2h_maps)
        total=max(0.0,pv_w+net_grid+dis-ch);base=max(0.0,total-max(0.0,ctrl))
        if base>5000: rejected+=1;continue
        buckets.setdefault((key.weekday(),key.hour),[]).append(base);days.add(key.date())
    allv=[v for xs in buckets.values() for v in xs if v>0];global_med=median(allv) if allv else 500.0
    slots=[]
    for n in range(hours):
        start=now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=n)
        vals=[v for v in buckets.get((start.weekday(),start.hour),[]) if v>0];source="PROFILE"
        if len(vals)<4: vals=[v for (wd,h),xs in buckets.items() if h==start.hour for v in xs if v>0]
        if vals: watts=median(vals);quality="GOOD" if len(vals)>=8 else "LEARNING"
        else:
            neigh=[v for d in (-2,-1,1,2) for (wd,h),xs in buckets.items() if h==(start.hour+d)%24 for v in xs if v>0]
            watts=median(neigh) if neigh else global_med;source="NEIGHBOUR_FALLBACK" if neigh else "GLOBAL_FALLBACK";quality="FALLBACK"
        slots.append({"start":start,"kwh":max(100.0,watts)/1000.0,"samples":len(vals),"quality":quality,"source":source})
    learned=len(days);q="GOOD" if learned>=21 else ("MEDIUM" if learned>=7 else "LEARNING")
    return {"model":"INS_EI_BASE_LOAD_PROFILE_V4","quality":q,"learned_days":learned,"rejected_points":rejected,"total_kwh":sum(x["kwh"] for x in slots),"slots":slots}


def _weather_hours(latitude: float, longitude: float, timezone: str) -> dict:
    params={"latitude":latitude,"longitude":longitude,"hourly":"cloud_cover,shortwave_radiation","forecast_days":3,"timezone":timezone}
    url="https://api.open-meteo.com/v1/forecast?"+urlencode(params)
    with urlopen(Request(url,headers={"User-Agent":"INS-EI-Core/1.0"}),timeout=10) as response:
        data=json.loads(response.read().decode())
    hourly=data.get("hourly") or {};out={}
    for ts,cloud,rad in zip(hourly.get("time",[]),hourly.get("cloud_cover",[]),hourly.get("shortwave_radiation",[])):
        out[ts]={"cloud_cover":float(cloud or 0),"shortwave_radiation":float(rad or 0)}
    return out


def pv_profile_v2(historian, site_id: str, component_kinds: dict[str,str], timezone: str, hours: int=24, latitude: float|None=None, longitude: float|None=None, component_properties=None):
    """Learned site PV profile with conservative weather attenuation from legacy V2."""
    tz=ZoneInfo(timezone);now=datetime.now(tz);hours=max(1,min(int(hours),48))
    component_properties=component_properties or {}
    pvs=_balance_components(component_kinds,component_properties,"PV","BALANCE_PV")
    by_hour={};days=set()
    # Sum logical PV components per timestamp approximately; use all observations to learn real site geometry.
    for c in pvs:
        for row in historian.numeric_series(site_id,c,"pv.generation_power",50000):
            ts=datetime.fromisoformat(row["observed_at"]).astimezone(tz)
            by_hour.setdefault(ts.hour,[]).append(max(0.0,row["value"]));days.add(ts.date())
    weather={}
    if latitude is not None and longitude is not None:
        try: weather=_weather_hours(latitude,longitude,timezone)
        except Exception: weather={}
    slots=[]
    for n in range(hours):
        start=now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=n);vals=by_hour.get(start.hour,[])
        learned_w=median(vals) if vals else 0.0
        wx=weather.get(start.strftime("%Y-%m-%dT%H:%M"));factor=1.0
        if wx and learned_w>0:
            cloud=max(0.0,min(100.0,wx["cloud_cover"]));factor=max(0.18,1.0-0.0075*cloud)
        watts=learned_w*factor
        if watts<50: watts=0.0
        slots.append({"start":start,"kwh":watts/1000.0,"baseline_kwh":learned_w/1000.0,"samples":len(vals),"quality":"GOOD" if len(vals)>=12 and len(days)>=7 and wx else "LEARNING","source":"HISTORICAL_PV_PLUS_WEATHER" if wx else "HISTORICAL_PV_PROFILE","cloud_cover_pct":wx["cloud_cover"] if wx else None,"shortwave_radiation_w_m2":wx["shortwave_radiation"] if wx else None,"weather_factor":factor if wx else None})
    learned=len(days);q="GOOD" if learned>=21 and weather else ("MEDIUM" if learned>=7 and weather else "LEARNING")
    return {"model":"INS_EI_PV_PROFILE_V2","quality":q,"learned_days":learned,"weather_used":bool(weather),"total_kwh":sum(x["kwh"] for x in slots),"baseline_total_kwh":sum(x["baseline_kwh"] for x in slots),"slots":slots}


def publish_forecast(timeseries, consumption: dict, pv: dict):
    now=datetime.now().astimezone()
    for name,data in (("forecast.consumption_energy",consumption),("forecast.pv_energy",pv)):
        slots=[TimeSlot(series=name,start=x["start"],end=x["start"]+timedelta(hours=1),value=round(x["kwh"],3),unit="kWh",quality=Quality.GOOD,generated_at=now,source=data["model"],metadata={"quality":x["quality"],"samples":x["samples"],"source":x["source"]}) for x in data["slots"]]
        timeseries.replace(name,slots)
