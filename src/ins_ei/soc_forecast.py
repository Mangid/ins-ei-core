from __future__ import annotations
from datetime import datetime,timedelta
from .models import Quality
from .timeseries import TimeSlot

def baseline_soc_forecast(timeseries,state,battery_id,capacity_kwh,min_soc_pct=20.0,efficiency=0.94,hours=24):
    soc_point=state.get(battery_id,"battery.soc")
    if not soc_point:return {"status":"NO_SOC","slots":[]}
    soc=max(0.0,min(100.0,float(soc_point.value)));usable_capacity=float(capacity_kwh)
    load=timeseries.series("forecast.consumption_energy")[:hours];pv=timeseries.series("forecast.pv_energy")[:hours]
    n=min(len(load),len(pv),hours);now=datetime.now().astimezone();slots=[]
    for i in range(n):
        net=float(pv[i].value)-float(load[i].value)
        energy=usable_capacity*soc/100.0
        if net>=0:energy+=net*efficiency
        else:energy+=net/efficiency
        floor=usable_capacity*float(min_soc_pct)/100.0
        energy=max(floor,min(usable_capacity,energy));soc=100.0*energy/usable_capacity
        start=load[i].start
        slots.append(TimeSlot(series="forecast.battery_soc",start=start,end=start+timedelta(hours=1),value=round(soc,2),unit="%",quality=Quality.GOOD,generated_at=now,source="BASELINE_ENERGY_BALANCE",metadata={"net_pv_minus_base_kwh":round(net,3),"min_soc_pct":min_soc_pct}))
    timeseries.replace("forecast.battery_soc",slots)
    return {"status":"OK","slots":len(slots),"start_soc_pct":float(soc_point.value),"min_soc_pct":min_soc_pct,"capacity_kwh":capacity_kwh}
