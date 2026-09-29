from __future__ import annotations

from fastapi.responses import HTMLResponse


def index_html() -> HTMLResponse:
    return HTMLResponse("""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>INS-EI</title>
<style>
:root{font-family:Inter,system-ui,sans-serif;color-scheme:dark;background:#0b0e12;color:#eef2f6}
body{margin:0;background:#0b0e12} header{padding:18px 24px;border-bottom:1px solid #252b34;display:flex;justify-content:space-between}
main{padding:20px;display:grid;gap:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.card{background:#131820;border:1px solid #252b34;border-radius:14px;padding:16px}.title{font-size:13px;color:#9ca8b7;text-transform:uppercase;letter-spacing:.08em}
.big{font-size:26px;font-weight:700;margin-top:8px}.ok{color:#78d69c}.warn{color:#f0c66b}.bad{color:#ff8080}
iframe{width:100%;height:620px;border:0;background:white;border-radius:10px;margin-top:12px}
table{width:100%;border-collapse:collapse;margin-top:10px}td,th{text-align:left;padding:8px;border-bottom:1px solid #252b34;font-size:14px}
.modelDetail{margin-top:10px;padding:12px;background:#0d1117;border:1px solid #252b34;border-radius:8px;font-size:13px;line-height:1.5}
.modelDetail h4{margin:10px 0 5px}.modelDetail dl{display:grid;grid-template-columns:minmax(150px,1fr) 1fr;gap:4px 12px;margin:5px 0}.modelDetail dt{color:#9ca8b7}.modelDetail dd{margin:0;text-align:right}
.modelRow{cursor:pointer}.modelRow:hover{background:#181e27}
button{background:#252b34;color:#fff;border:1px solid #394250;border-radius:8px;padding:8px 12px;cursor:pointer}
</style>
</head>
<body>
<header><div><b>INS-EI</b> <span style="color:#7f8b99">V1 · v0.1.34 · Learning Platform</span></div><div><button onclick="location.href='config'">⚙ Konfiguration</button> <button onclick="refresh()">Aktualisieren</button></div></header>
<main>
<div class="grid">
 <div class="card"><div class="title">Core</div><div id="health" class="big">…</div><div id="site"></div></div>
 <div class="card"><div class="title">Safety</div><div id="safety" class="big">…</div><div id="safetyReason"></div></div>
 <div class="card"><div class="title">Learning</div><div id="models" class="big">…</div><div id="learningDetail">registrierte Modelle</div></div>
 <div class="card"><div class="title">Autonomie</div><div id="auto" class="big">…</div><div>Capabilities konfiguriert</div></div>
</div>
<div class="card"><div class="title">Thermal Shadow · supervised</div>
 <div id="thermalShadow">Lade…</div>
 <div style="margin-top:10px"><button onclick="heatOnce(true)">WW einmal laden</button> <button onclick="heatOnce(false)">Heat Once beenden</button> <span id="heatOnceResult"></span></div>
 <small>Physische Befehle werden nur nach deinem Klick ausgeführt. Keine automatische Freigabe.</small>
</div>
<div class="card"><div class="title">Anlage · automatisch aus SiteGraph</div><iframe src="./site/schema.svg"></iframe></div>
<div class="grid">
 <div class="card"><div class="title">Plugin Health</div><table id="plugins"><tbody></tbody></table></div>
 <div class="card"><div class="title">Learning Modelle</div><table id="learningModels"><tbody></tbody></table><div id="modelDetails"></div></div>
 <div class="card"><div class="title">Capability Autonomy</div><table id="autonomy"><tbody></tbody></table></div>
</div>
</main>
<script>
function api(path){
 const base=window.location.pathname.endsWith('/')?window.location.pathname:window.location.pathname+'/';
 return base+path.replace(/^\//,'');
}
async function j(url){
 const r=await fetch(api(url));
 const text=await r.text();
 if(!r.ok) throw new Error(url+' HTTP '+r.status+' '+text.slice(0,160));
 try{return JSON.parse(text)}catch(e){throw new Error(url+' invalid JSON: '+text.slice(0,160))}
}
function cls(v){return ['OK','RUNNING','AUTONOMOUS'].includes(v)?'ok':['FAILED','DEGRADED'].includes(v)?'bad':'warn'}

function fmt(v,d=2){return v==null?'–':(typeof v==='number'?v.toFixed(d):v)}
function kv(obj, units={}){
 return '<dl>'+Object.entries(obj||{}).map(([k,v])=>'<dt>'+k.replaceAll('_',' ')+'</dt><dd>'+fmt(v)+(units[k]||'')+'</dd>').join('')+'</dl>'
}
function modelDetail(m){
 const md=m.metadata||{};
 const fit=m.id==='battery-baseline'?(md.battery_fit||md.fit||{}):
           m.id==='electrical-baseline'?(md.electrical_fit||md.fit||{}):
           (md.fit||md.generic_fit||{});
 let html='<div class="modelDetail"><b>'+m.id+'</b><br><span class="muted">'+(m.reason||'')+'</span>'+
   '<dl><dt>Phase</dt><dd>'+(md.phase||'–')+'</dd><dt>Letzter Fit</dt><dd>'+(md.last_fit_at||'–')+'</dd><dt>Status</dt><dd>'+m.status+'</dd></dl>';
 if(m.id==='thermal-baseline'){
   const ctx=md.thermal_context_fit||{};
   html+='<h4>Puffer · Kontext</h4>';
   Object.entries(ctx).forEach(([name,x])=>{html+='<b>'+name+'</b>'+kv(x,{mean_delta_c_per_h:' °C/h',median_delta_c_per_h:' °C/h',p025_delta_c_per_h:' °C/h',p975_delta_c_per_h:' °C/h',raw_min_delta_c_per_h:' °C/h',raw_max_delta_c_per_h:' °C/h',mean_outdoor_c:' °C'})});
   if(md.dhw_fit){html+='<h4>Warmwasser</h4>';Object.entries(md.dhw_fit).forEach(([name,x])=>{if(x)html+='<b>'+name+'</b>'+kv(x,{mean_delta_c_per_h:' °C/h',median_delta_c_per_h:' °C/h'})})}
 } else if(m.id==='battery-baseline'){
   html+='<h4>Batterie</h4>';
   ['soc','voltage_dc','current_dc','charge_power','discharge_power'].forEach(k=>{if(fit[k])html+='<b>'+k.replaceAll('_',' ')+'</b>'+kv(fit[k])});
   html+=kv({observed_charge_wh:fit.observed_charge_wh,observed_discharge_wh:fit.observed_discharge_wh,observed_soc_span_pct:fit.observed_soc_span_pct},{observed_charge_wh:' Wh',observed_discharge_wh:' Wh',observed_soc_span_pct:' %'});
 } else if(m.id==='electrical-baseline'){
   html+='<h4>Elektrische Daten</h4>';
   Object.entries(fit).forEach(([name,x])=>{html+='<b>'+name.replaceAll('_',' ')+'</b>'+kv(x)});
 } else if(m.id==='pv-orientation-baseline'){
   const ori=md.orientation_fit||{}, inputs=md.input_fit||{};
   html+='<h4>Ausrichtungen</h4>';
   Object.entries(ori).forEach(([name,x])=>{html+='<b>'+name+'</b>'+kv(x,{capacity_kwp:' kWp',maximum_w:' W',mean_w:' W',maximum_w_per_kwp:' W/kWp',energy_wh_observed:' Wh',energy_wh_per_kwp:' Wh/kWp'})});
   html+='<h4>PV-Eingänge</h4>';
   Object.entries(inputs).forEach(([name,x])=>{html+='<b>'+name+'</b>'+kv(x,{maximum_w:' W',mean_w:' W',energy_wh_observed:' Wh',maximum_w_per_kwp:' W/kWp'})});
 }
 return html+'</div>';
}
function showModel(id){const m=window.learningModelData.find(x=>x.id===id);modelDetails.innerHTML=m?modelDetail(m):''}


async function heatOnce(enabled){
 const label=enabled?'WW-Einmalladung STARTEN':'WW-Einmalladung BEENDEN';
 if(!confirm(label+'? Dies sendet einen physischen Befehl an die ÖkoFEN-Regelung.')) return;
 heatOnceResult.textContent=' sende…';
 try{
   const r=await fetch(api('/supervised/oekofen/heat-once?enabled='+enabled),{method:'POST'});
   const text=await r.text(); let d={}; try{d=JSON.parse(text)}catch(_e){}
   heatOnceResult.textContent=r.ok?' ✓ ausgeführt · '+(d.correlation_id||''):' ✗ '+(d.detail||text||('HTTP '+r.status));
   heatOnceResult.className=r.ok?'ok':'bad';
 }catch(e){heatOnceResult.textContent=' ✗ '+e;heatOnceResult.className='bad'}
}

async function refresh(){
 const results=await Promise.allSettled([
   j('/health'),j('/safety'),j('/learning/models'),j('/learning/status'),j('/autonomy'),j('/state')
 ]);
 const [rh,rs,rl,rls,ra,rstate]=results;
 if(rh.status==='fulfilled'){
   const h=rh.value; health.textContent=h.status; health.className='big '+cls(h.status); site.textContent=h.site;
   plugins.innerHTML=Object.entries(h.plugins).map(([k,v])=>'<tr><td>'+k+'</td><td class="'+cls(v.status)+'">'+v.status+'</td><td>'+(v.last_read_age_seconds==null?'–':Math.round(v.last_read_age_seconds)+' s')+'</td></tr>').join('');
 } else {health.textContent='API FEHLER';health.className='big bad';site.textContent=rh.reason.message}
 if(rs.status==='fulfilled'){
   const s=rs.value;safety.textContent=s.emergency_stop?'NOT-AUS AKTIV':'Freigegeben';safety.className='big '+(s.emergency_stop?'bad':'ok');safetyReason.textContent=s.reason||'';
 } else {safety.textContent='API FEHLER';safety.className='big bad';safetyReason.textContent=rs.reason.message}
 if(rl.status==='fulfilled'){
   const l=rl.value;window.learningModelData=l.models;
   learningModels.innerHTML=l.models.map(x=>'<tr class="modelRow" data-model-id="'+x.id+'"><td>'+x.id+'</td><td class="'+cls(x.status)+'">'+x.status+'</td><td>'+((x.metadata&&x.metadata.phase)||'OBSERVATION')+'</td></tr>').join('');
   learningModels.querySelectorAll('[data-model-id]').forEach(row=>row.addEventListener('click',()=>showModel(row.dataset.modelId)));
   models.textContent=l.models.length;
 } else {models.textContent='API FEHLER';models.className='big bad';learningDetail.textContent=rl.reason.message}
 if(rls.status==='fulfilled'){
   const ls=rls.value;
   if(rl.status==='fulfilled') models.textContent=rl.value.models.length+' · '+ls.phase;
   learningDetail.textContent=ls.duration_hours.toFixed(1)+' h · '+ls.samples+' Samples · '+ls.signals+' Signale';
 } else {learningDetail.textContent=rls.reason.message}
 if(rstate.status==='fulfilled'){
   const pts=rstate.value.points||[];
   const dhwDecision=pts.find(x=>x.component_id==='dhw'&&x.point==='decision.dhw');
   const genDecision=pts.find(x=>x.component_id==='pellet_boiler'&&x.point==='decision.heat_generator');
   const heatOnceState=pts.find(x=>x.component_id==='dhw'&&x.point==='state.one_time_charge');
   const peMode=pts.find(x=>x.component_id==='pellet_boiler'&&x.point==='state.operating_mode');
   thermalShadow.innerHTML='<b>DHW:</b> '+(dhwDecision?dhwDecision.value:'–')+
     ' &nbsp; <b>Heat Once:</b> '+(heatOnceState?heatOnceState.value:'–')+
     '<br><b>Wärmeerzeuger:</b> '+(genDecision?genDecision.value:'–')+
     ' &nbsp; <b>pe_mode:</b> '+(peMode?peMode.value:'–');
 }
 if(ra.status==='fulfilled'){
   const a=ra.value;auto.textContent=a.capabilities.length;
   autonomy.innerHTML=a.capabilities.map(x=>'<tr><td>'+x.capability+'</td><td class="'+cls(x.mode)+'">'+x.mode+'</td><td>'+(x.assessment.allowed?'EXECUTE':'BLOCK')+'</td></tr>').join('');
 } else {auto.textContent='API FEHLER';auto.className='big bad';autonomy.innerHTML='<tr><td>'+ra.reason.message+'</td></tr>'}
}
refresh(); setInterval(refresh,10000)
</script></body></html>""")
