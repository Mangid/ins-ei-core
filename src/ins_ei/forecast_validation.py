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
