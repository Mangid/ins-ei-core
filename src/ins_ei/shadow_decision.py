from __future__ import annotations
from statistics import median

def shadow_decisions(timeseries,hours=24):
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
        battery="HOLD";thermal="HOLD";heat_source="NORMAL";reasons=[]
        if net>0.25:
            if s<95:battery="CHARGE_PV";reasons.append("PV-Überschuss und Batteriespeicher frei")
            elif sell is not None and export_med is not None and sell>=export_med:
                battery="HOLD";thermal="EXPORT_PREFERRED";reasons.append("Batterie voll und Einspeisewert attraktiv")
            else:thermal="USE_PV_SURPLUS";reasons.append("PV-Überschuss thermisch nutzbar")
        elif net<-0.25:
            if s>25:battery="DISCHARGE";reasons.append("Verbrauch über PV bei ausreichendem SOC")
            elif buy is not None and import_med is not None and buy<import_med*0.75:
                battery="GRID_CHARGE_CANDIDATE";reasons.append("niedriger SOC und günstiger Bezug")
            else:reasons.append("PV-Defizit; Batterie wird geschont")
        future_pv=sum(float(x.value) for x in pv[i:min(n,i+6)])
        if future_pv>=4.0:heat_source="DEFER_IF_SAFE";reasons.append("in den nächsten 6 h ist nutzbarer PV-Ertrag prognostiziert")
        slots.append({"start":load[i].start.isoformat(),"load_kwh":round(l,3),"pv_kwh":round(p,3),"net_kwh":round(net,3),"soc_pct":round(s,1),"import_ct_kwh":buy,"export_ct_kwh":sell,"battery":battery,"thermal":thermal,"heat_source":heat_source,"reason":"; ".join(reasons)})
    return {"status":"SHADOW","mode":"OBSERVE_ONLY","slots":slots}
