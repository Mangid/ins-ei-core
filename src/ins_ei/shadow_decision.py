from __future__ import annotations
from statistics import median

def shadow_decisions(timeseries,thermal=None,hours=24):
    thermal=thermal or {"status":"UNKNOWN","can_defer_heat":False,"can_accept_p2h":False,"reason":"Thermal Guard unbekannt"}
    load=timeseries.series("forecast.consumption_energy")[:hours]
    pv=timeseries.series("forecast.pv_energy")[:hours]
    soc=timeseries.series("forecast.battery_soc")[:hours]
    imp=timeseries.series("market.import_price")[:hours]
    exp=timeseries.series("market.export_price")[:hours]
    n=min(len(load),len(pv),len(soc),hours)
    if not n:return {"status":"LEARNING","slots":[]}
    import_values=[float(x.value) for x in imp[:n]]
    export_values=[float(x.value) for x in exp[:n]]
    import_med=median(import_values) if import_values else None
    export_med=median(export_values) if export_values else None
    slots=[]
    for i in range(n):
        l=float(load[i].value);p=float(pv[i].value);s=float(soc[i].value);net=p-l
        buy=float(imp[i].value) if i<len(imp) else None
        sell=float(exp[i].value) if i<len(exp) else None
        battery="HOLD";thermal_action="HOLD";heat_source="NORMAL";reasons=[]
        if net>0.25:
            if s<95:battery="CHARGE_PV";reasons.append("PV-Überschuss und Batteriespeicher frei")
            elif sell is not None and export_med is not None and sell>=export_med:
                battery="HOLD";thermal_action="EXPORT_PREFERRED";reasons.append("Batterie voll und Einspeisewert attraktiv")
            elif thermal.get("can_accept_p2h"):thermal_action="USE_PV_SURPLUS";reasons.append("PV-Überschuss und thermische Aufnahmefähigkeit vorhanden")
            else:thermal_action="HOLD";reasons.append("PV-Überschuss vorhanden, aber keine thermische Aufnahmefähigkeit freigegeben")
        elif net<-0.25:
            if s>25:battery="DISCHARGE";reasons.append("Verbrauch über PV bei ausreichendem SOC")
            elif buy is not None and import_med is not None and buy<import_med*0.75:
                battery="GRID_CHARGE_CANDIDATE";reasons.append("niedriger SOC und günstiger Bezug")
            else:reasons.append("PV-Defizit; Batterie wird geschont")
        future_pv=sum(float(x.value) for x in pv[i:min(n,i+6)])
        if future_pv>=4.0 and thermal.get("can_defer_heat"):heat_source="DEFER_IF_SAFE";reasons.append("PV-Ertrag erwartet und Thermal Guard erlaubt Zurückhalten")
        elif future_pv>=4.0:reasons.append("PV-Ertrag erwartet, aber Thermal Guard erlaubt kein Zurückhalten")
        slots.append({"start":load[i].start.isoformat(),"load_kwh":round(l,3),"pv_kwh":round(p,3),"net_kwh":round(net,3),"soc_pct":round(s,1),"import_ct_kwh":buy,"export_ct_kwh":sell,"battery":battery,"thermal":thermal_action,"heat_source":heat_source,"reason":"; ".join(reasons)})
    return {"status":"SHADOW","mode":"OBSERVE_ONLY","thermal_guard":thermal,"slots":slots}
