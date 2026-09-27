from __future__ import annotations
from fastapi.responses import HTMLResponse

def setup_html() -> HTMLResponse:
    return HTMLResponse("""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>INS-EI Setup</title>
<style>body{font-family:system-ui;background:#0b0e12;color:#eef2f6;margin:0}main{max-width:900px;margin:auto;padding:28px}.card{background:#131820;border:1px solid #29313b;border-radius:14px;padding:18px;margin:14px 0}input{width:100%;box-sizing:border-box;background:#0b0e12;color:white;border:1px solid #394554;border-radius:8px;padding:10px;margin:6px 0 12px}button{padding:10px 14px;border:0;border-radius:8px;cursor:pointer}button.primary{background:#e8eef6;color:#111}small{color:#9aa7b6}.ok{color:#7bd89d}.bad{color:#ff8585}</style></head>
<body><main><h1>INS-EI</h1><p>Neue Anlage einrichten · Learning / Shadow</p>
<div class="card"><h3>1 · Anlage</h3><label>Name / ID</label><input id="siteId" value="home-v1"><label>Zeitzone</label><input id="timezone" value="Europe/Vienna"></div>
<div id="plugins"></div>
<div class="card"><h3>3 · Speichern</h3><p><small>V1 speichert die Konfiguration lokal. Nach dem Speichern wird INS-EI neu gestartet und baut daraus den SiteGraph.</small></p><button class="primary" onclick="save()">Konfiguration speichern</button><div id="saveResult"></div></div>
<script>
let manifests=[], instances=[];
async function load(){const r=await fetch('/setup/plugins');const d=await r.json();manifests=d.plugins;render()}
function render(){plugins.innerHTML='<h2>2 · Geräte</h2>'+manifests.map(p=>'<div class="card"><h3>'+p.name+'</h3><small>'+p.capabilities.join(' · ')+'</small><div id="f_'+p.id+'">'+(p.config_schema.fields||[]).map(f=>'<label>'+f.label+'</label><input data-plugin="'+p.id+'" data-field="'+f.id+'" type="'+(f.type==='password'?'password':'text')+'" value="'+(f.default??'')+'">').join('')+'</div><button onclick="testPlugin(\''+p.id+'\')">Verbindung testen</button> <span id="r_'+p.id+'"></span></div>').join('')}
function cfg(id){let o={};document.querySelectorAll('[data-plugin="'+id+'"]').forEach(x=>{if(x.value!=='')o[x.dataset.field]=x.dataset.field==='port'||x.dataset.field==='unit_id'?Number(x.value):x.value});return o}
async function testPlugin(id){const el=document.getElementById('r_'+id);el.textContent=' teste…';const r=await fetch('/setup/test-plugin',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({plugin_id:id,instance_id:id+'_main',config:cfg(id)})});const d=await r.json();el.className=r.ok?'ok':'bad';el.textContent=r.ok?' ✓ '+d.points.length+' Punkte':' ✗ '+(d.detail||'Fehler')}
async function save(){const plugin_instances=manifests.filter(p=>Object.keys(cfg(p.id)).length).map(p=>({id:p.id.replace('-','_')+'_main',plugin:p.id,config:cfg(p.id)}));const payload={site_id:siteId.value,timezone:timezone.value,plugin_instances,components:[],relations:[],connections:[],constraints:[],apps:{},strategy:{modules:[]},site_rules:[]};const r=await fetch('/setup/save',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();saveResult.textContent=d.saved?'Gespeichert. INS-EI neu starten.':'Fehler'}
load()</script></main></body></html>""")
