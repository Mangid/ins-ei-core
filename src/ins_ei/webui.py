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
button{background:#252b34;color:#fff;border:1px solid #394250;border-radius:8px;padding:8px 12px;cursor:pointer}
</style>
</head>
<body>
<header><div><b>INS-EI</b> <span style="color:#7f8b99">V1 · v0.1.16 · Learning Platform</span></div><div><button onclick="location.href='config'">⚙ Konfiguration</button> <button onclick="refresh()">Aktualisieren</button></div></header>
<main>
<div class="grid">
 <div class="card"><div class="title">Core</div><div id="health" class="big">…</div><div id="site"></div></div>
 <div class="card"><div class="title">Safety</div><div id="safety" class="big">…</div><div id="safetyReason"></div></div>
 <div class="card"><div class="title">Learning</div><div id="models" class="big">…</div><div>registrierte Modelle</div></div>
 <div class="card"><div class="title">Autonomie</div><div id="auto" class="big">…</div><div>Capabilities konfiguriert</div></div>
</div>
<div class="card"><div class="title">Anlage · automatisch aus SiteGraph</div><iframe src="./site/schema.svg"></iframe></div>
<div class="grid">
 <div class="card"><div class="title">Plugin Health</div><table id="plugins"><tbody></tbody></table></div>
 <div class="card"><div class="title">Capability Autonomy</div><table id="autonomy"><tbody></tbody></table></div>
</div>
</main>
<script>
function api(path){
 const base=window.location.pathname.endsWith('/')?window.location.pathname:window.location.pathname+'/';
 return base+path.replace(/^\//,'');
}
async function j(url){const r=await fetch(api(url));return r.json()}
function cls(v){return ['OK','RUNNING','AUTONOMOUS'].includes(v)?'ok':['FAILED','DEGRADED'].includes(v)?'bad':'warn'}
async function refresh(){
 const [h,s,l,a]=await Promise.all([j('/health'),j('/safety'),j('/learning/models'),j('/autonomy')])
 health.textContent=h.status; health.className='big '+cls(h.status); site.textContent=h.site
 safety.textContent=s.emergency_stop?'NOT-AUS AKTIV':'Freigegeben'; safety.className='big '+(s.emergency_stop?'bad':'ok'); safetyReason.textContent=s.reason||''
 models.textContent=l.models.length; auto.textContent=a.capabilities.length
 plugins.innerHTML=Object.entries(h.plugins).map(([k,v])=>'<tr><td>'+k+'</td><td class="'+cls(v.status)+'">'+v.status+'</td><td>'+(v.last_read_age_seconds==null?'–':Math.round(v.last_read_age_seconds)+' s')+'</td></tr>').join('')
 autonomy.innerHTML=a.capabilities.map(x=>'<tr><td>'+x.capability+'</td><td class="'+cls(x.mode)+'">'+x.mode+'</td><td>'+(x.assessment.allowed?'EXECUTE':'BLOCK')+'</td></tr>').join('')
}
refresh(); setInterval(refresh,10000)
</script></body></html>""")
