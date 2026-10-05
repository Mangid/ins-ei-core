from __future__ import annotations
from datetime import datetime,timedelta
from statistics import mean

def _hour(rows):
    out={}
    for r in rows:
        ts=datetime.fromisoformat(r["observed_at"]).replace(minute=0,second=0,microsecond=0)
        out.setdefault(ts,[]).append(float(r["value"]))
    return {k:mean(v) for k,v in out.items()}

def _select(component_kinds, component_properties, kind, role):
    candidates=[c for c,k in component_kinds.items() if k==kind]
    explicit=[c for c in candidates if (component_properties.get(c,{}) or {}).get('forecast_role')==role]
    if explicit:return explicit
    # Never sum multiple logical representations implicitly. Ambiguity must be commissioned.
    return candidates if len(candidates)<=1 else []


def validate_energy_balance(historian,site_id,component_kinds,hours=168,component_properties=None):
    """Validate reconstructed inflexible load; flexible P2H is explicitly excluded."""
    component_properties=component_properties or {}
    grids=_select(component_kinds,component_properties,"GRID","BALANCE_GRID")
    pvs=_select(component_kinds,component_properties,"PV","BALANCE_PV")
    bats=_select(component_kinds,component_properties,"BATTERY","BALANCE_BATTERY")
    p2hs=[c for c,k in component_kinds.items() if k=="POWER_TO_HEAT"]
    ambiguous={kind:[c for c,k in component_kinds.items() if k==kind] for kind in ("GRID","PV","BATTERY") if len([c for c,k in component_kinds.items() if k==kind])>1 and not _select(component_kinds,component_properties,kind,{"GRID":"BALANCE_GRID","PV":"BALANCE_PV","BATTERY":"BALANCE_BATTERY"}[kind])}
    if ambiguous:return {"hours":0,"reason":"AMBIGUOUS_BALANCE_SOURCE","ambiguous":ambiguous,"required_property":"forecast_role"}
    if not grids:return {"hours":0,"reason":"NO_GRID"}
    imp=_hour(historian.numeric_series(site_id,grids[0],"grid.import_power",50000))
    exp=_hour(historian.numeric_series(site_id,grids[0],"grid.export_power",50000))
    pv=[_hour(historian.numeric_series(site_id,c,"pv.generation_power",50000)) for c in pvs]
    ch=[_hour(historian.numeric_series(site_id,c,"battery.charge_power",50000)) for c in bats]
    dis=[_hour(historian.numeric_series(site_id,c,"battery.discharge_power",50000)) for c in bats]
    flex=[_hour(historian.numeric_series(site_id,c,"power.electrical",50000)) for c in p2hs]
    cutoff=datetime.now().astimezone()-timedelta(hours=hours);rows=[]
    for ts,iv in imp.items():
        if ts<cutoff:continue
        pv_w=sum(x.get(ts,0) for x in pv);net=iv-exp.get(ts,0)
        ch_w=sum(x.get(ts,0) for x in ch);dis_w=sum(x.get(ts,0) for x in dis)
        flex_w=sum(max(0,x.get(ts,0)) for x in flex)
        total=max(0,pv_w+net+dis_w-ch_w);base=max(0,total-flex_w)
        rows.append({"start":ts.isoformat(),"pv_kwh":pv_w/1000,"grid_import_kwh":iv/1000,"grid_export_kwh":exp.get(ts,0)/1000,"battery_charge_kwh":ch_w/1000,"battery_discharge_kwh":dis_w/1000,"flexible_p2h_kwh":flex_w/1000,"reconstructed_total_kwh":total/1000,"inflexible_base_kwh":base/1000})
    return {"hours":len(rows),"sources":{"grid":grids,"pv":pvs,"battery":bats,"power_to_heat":p2hs},"flexible_loads_excluded":["POWER_TO_HEAT"],"rows":rows,"totals":{k:round(sum(r[k] for r in rows),3) for k in ("pv_kwh","grid_import_kwh","grid_export_kwh","battery_charge_kwh","battery_discharge_kwh","flexible_p2h_kwh","reconstructed_total_kwh","inflexible_base_kwh")}}

def score_slots(forecast_slots, actual_by_hour):
    errors=[]
    for slot in forecast_slots:
        key=slot.start.replace(minute=0,second=0,microsecond=0)
        if key not in actual_by_hour:continue
        f=float(slot.value);a=float(actual_by_hour[key]);errors.append(a-f)
    if not errors:return {"samples":0,"mae_kwh":None,"bias_kwh":None}
    return {"samples":len(errors),"mae_kwh":round(mean(abs(x) for x in errors),3),"bias_kwh":round(mean(errors),3)}


def daily_base_diagnostics(validation: dict, forecast_slots: list | None = None) -> dict:
    """Compare validated historical inflexible load by day with current 24h forecast."""
    by_day={}
    for row in validation.get("rows",[]):
        day=str(row["start"])[:10]
        by_day[day]=by_day.get(day,0.0)+float(row.get("inflexible_base_kwh",0))
    days=[{"day":d,"actual_base_kwh":round(v,3)} for d,v in sorted(by_day.items())]
    complete=[x["actual_base_kwh"] for x in days[:-1] if x["actual_base_kwh"]>0] if len(days)>1 else []
    current=sum(float(getattr(s,"value",0) or 0) for s in (forecast_slots or [])[:24])
    avg=mean(complete) if complete else None
    return {
        "historical_days":days,
        "complete_days":len(complete),
        "historical_daily_mean_kwh":round(avg,3) if avg is not None else None,
        "current_forecast_24h_kwh":round(current,3),
        "forecast_vs_history_ratio":round(current/avg,3) if avg else None,
    }
