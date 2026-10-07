from __future__ import annotations

def _value(state,component,*points):
    for name in points:
        p=state.get(component,name)
        if p is not None and getattr(p,"value",None) is not None:return float(p.value)
    return None

def thermal_guard(state,site):
    """Simple observable thermal permission; never invents stored kWh."""
    constraints=site.constraints
    def limit(cid,typ,default=None):
        vals=[float(x.get("value")) for x in constraints if x.get("target")==cid and x.get("type")==typ]
        return vals[0] if vals else default
    buffer_top=_value(state,"buffer","thermal.temperature_upper","thermal.temperature")
    buffer_lower=_value(state,"buffer","thermal.temperature_lower","thermal.temperature_bottom")
    dhw=_value(state,"dhw","thermal.temperature_upper","thermal.temperature","thermal.temperature_bottom")
    buffer_max=limit("buffer","MAX_VALUE",78.0)
    dhw_min=limit("dhw","MIN_VALUE",40.0)
    dhw_max=limit("dhw","MAX_VALUE",55.0)
    known=buffer_top is not None or buffer_lower is not None or dhw is not None
    if not known:return {"status":"UNKNOWN","can_defer_heat":False,"can_accept_p2h":False,"reason":"keine aktuellen thermischen Temperaturen verfügbar"}
    comfort_risk=dhw is not None and dhw<=dhw_min
    buffer_headroom=any(t is not None and t<buffer_max-3 for t in (buffer_top,buffer_lower))
    dhw_headroom=dhw is not None and dhw<dhw_max-2
    can_accept=buffer_headroom or dhw_headroom
    can_defer=not comfort_risk and ((buffer_top is not None and buffer_top>45) or (dhw is not None and dhw>dhw_min+3))
    reasons=[]
    if comfort_risk:reasons.append(f"Warmwasser {dhw:.1f} °C nahe/unter Mindesttemperatur {dhw_min:.1f} °C")
    if buffer_headroom:reasons.append("Puffer hat thermische Aufnahmefähigkeit")
    if dhw_headroom:reasons.append("Warmwasser hat thermische Aufnahmefähigkeit")
    if can_defer:reasons.append("thermischer Zustand erlaubt zeitweises Zurückhalten")
    return {"status":"OK","can_defer_heat":can_defer,"can_accept_p2h":can_accept,"buffer_top_c":buffer_top,"buffer_lower_c":buffer_lower,"buffer_max_c":buffer_max,"dhw_c":dhw,"dhw_min_c":dhw_min,"dhw_max_c":dhw_max,"reason":"; ".join(reasons) or "keine thermische Verschiebung freigegeben"}
