from __future__ import annotations
from datetime import datetime,timedelta
from statistics import mean
from .forecast_validation import validate_energy_balance

def _actual_base(validation):
    return {datetime.fromisoformat(r["start"]).replace(minute=0,second=0,microsecond=0):float(r["inflexible_base_kwh"]) for r in validation.get("rows",[])}

def _actual_pv(validation):
    return {datetime.fromisoformat(r["start"]).replace(minute=0,second=0,microsecond=0):float(r["pv_kwh"]) for r in validation.get("rows",[])}

def _score(snapshots, actual, now):
    errors=[];rows=[]
    # use the latest forecast generated before each target hour
    grouped={}
    for s in snapshots:
        target=datetime.fromisoformat(s["target_start"])
        generated=datetime.fromisoformat(s["generated_at"])
        if target>=now or generated>target:continue
        if target not in grouped or generated>datetime.fromisoformat(grouped[target]["generated_at"]):grouped[target]=s
    for target,s in sorted(grouped.items()):
        if target not in actual:continue
        f=float(s["forecast_value"]);a=float(actual[target]);e=a-f
        errors.append(e);rows.append({"start":target.isoformat(),"forecast_kwh":round(f,3),"actual_kwh":round(a,3),"error_kwh":round(e,3)})
    return {"samples":len(errors),"mae_kwh":round(mean(abs(e) for e in errors),3) if errors else None,"bias_kwh":round(mean(errors),3) if errors else None,"rows":rows[-48:]}

def forecast_accuracy(historian,site_id,component_kinds,component_properties,hours=168):
    now=datetime.now().astimezone();since=now-timedelta(hours=hours)
    validation=validate_energy_balance(historian,site_id,component_kinds,hours=hours,component_properties=component_properties)
    return {
      "consumption":_score(historian.forecast_snapshots(site_id,"forecast.consumption_energy",since),_actual_base(validation),now),
      "pv":_score(historian.forecast_snapshots(site_id,"forecast.pv_energy",since),_actual_pv(validation),now),
    }
