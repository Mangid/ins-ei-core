from __future__ import annotations

from html import escape
from fastapi.responses import HTMLResponse


def setup_html(plugin_items=None, version: str = "0.1.13", existing_site=None) -> HTMLResponse:
    existing_site = existing_site or {}
    existing_instances = {x.get('plugin'): x for x in existing_site.get('plugin_instances', [])}
    plugin_items = [x for x in list(plugin_items or []) if x.manifest.kind != "test"]

    choices = []
    configs = []
    for item in plugin_items:
        m = item.manifest
        pid = escape(m.id)
        existing = existing_instances.get(m.id, {})
        existing_config = existing.get("config", {})
        checked = " checked" if existing else ""
        caps = " · ".join(m.capabilities)
        choices.append(
            f'<label class="pluginChoice"><input type="checkbox" data-select-plugin="{pid}"{checked} '
            f'onchange="syncPlugins()">'
            f'<span><b>{escape(m.name)}</b><small>{escape(caps)}</small></span></label>'
        )
        fields = []
        for field in m.config_schema.get("fields", []):
            fid = escape(str(field.get("id", "")))
            label = escape(str(field.get("label", fid)))
            ftype = "password" if field.get("type") == "password" else "text"
            raw_value = existing_config.get(field.get("id"), field.get("default", ""))
            default = escape(str(raw_value if raw_value is not None else ""))
            fields.append(
                f'<label>{label}</label><input data-plugin="{pid}" data-field="{fid}" '
                f'type="{ftype}" value="{default}">'
            )
        configs.append(
            f'<div class="pluginConfig" data-config-plugin="{pid}" hidden>'
            f'<div class="card"><h3>{escape(m.name)}</h3>{"".join(fields)}'
            f'<button onclick="testPlugin(\'{pid}\')">Verbindung testen</button> '
            f'<span id="r_{pid}"></span></div></div>'
        )

    return HTMLResponse(f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>INS-EI Setup</title>
<style>
body{{font-family:system-ui;background:#0b0e12;color:#eef2f6;margin:0}}main{{max-width:900px;margin:auto;padding:28px}}
header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}}small,.muted{{color:#9aa7b6}}
.card{{background:#131820;border:1px solid #29313b;border-radius:14px;padding:20px;margin:14px 0}}
input[type=text],input[type=password]{{width:100%;box-sizing:border-box;background:#0b0e12;color:white;border:1px solid #394554;border-radius:8px;padding:10px;margin:6px 0 14px}}
button{{padding:10px 14px;border:0;border-radius:8px;cursor:pointer}}button.primary{{background:#e8eef6;color:#111}}
.steps{{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}}.stepDot{{padding:7px 10px;border-radius:20px;background:#171d25;color:#8d99a8;font-size:13px}}.stepDot.active{{background:#e8eef6;color:#111}}
.page{{display:none}}.page.active{{display:block}}.actions{{display:flex;justify-content:space-between;margin-top:18px}}
.pluginGrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}
.pluginChoice{{display:flex;gap:12px;align-items:flex-start;background:#131820;border:1px solid #29313b;border-radius:12px;padding:16px;cursor:pointer}}
.pluginChoice input{{margin-top:4px;transform:scale(1.25)}}.pluginChoice span{{display:flex;flex-direction:column;gap:5px}}
.ok{{color:#7bd89d}}.bad{{color:#ff8585}}
</style></head><body><main>
<header><div><h1 style="margin:0">INS-EI</h1><small>V1 · v{escape(version)} · Inbetriebnahme</small></div><button onclick="history.length>1?history.back():location.href='./'">← Zurück</button></header>
<div class="steps"><span class="stepDot active">1 Grundeinstellungen</span><span class="stepDot">2 Plugins</span><span class="stepDot">3 Konfiguration</span><span class="stepDot">4 Komponenten</span><span class="stepDot">5 Anlage</span><span class="stepDot">6 Grenzen</span><span class="stepDot">7 Start</span></div>

<section class="page active">
<h2>Grundeinstellungen</h2><p class="muted">Zuerst legen wir nur die Anlage selbst an.</p>
<div class="card"><label>Name / ID</label><input id="siteId" type="text" value="{escape(str(existing_site.get('site', {}).get('id', 'home-v1')))}"><label>Zeitzone</label><input id="timezone" type="text" value="{escape(str(existing_site.get('site', {}).get('timezone', 'Europe/Vienna')))}"></div>
</section>

<section class="page">
<h2>Welche Plugins werden an dieser Anlage verwendet?</h2><p class="muted">Nur auswählen – die Gerätedaten kommen im nächsten Schritt.</p>
<div class="pluginGrid">{"".join(choices)}</div>
</section>

<section class="page">
<h2>Plugins konfigurieren</h2><p class="muted">Jetzt konfigurieren und testen wir nur die ausgewählten Geräte.</p>
<div id="pluginConfigs">{"".join(configs)}</div>
<div id="noneSelected" class="card muted">Noch kein Plugin ausgewählt.</div>
</section>

<section class="page"><h2>Erkannte Komponenten</h2><div class="card"><p class="muted">Nach erfolgreichen Verbindungstests erscheinen hier erkannte Kessel, Speicher, Batterie, PV, Zähler usw.</p><div id="discoveredComponents">Noch keine Komponenten erkannt.</div></div></section>
<section class="page"><h2>Anlage & Verbindungen</h2><p class="muted">INS-EI schlägt aus den erkannten Komponenten eine Grundtopologie vor. Du kannst Verbindungen entfernen oder ergänzen.</p><div id="topologyEditor"></div><div class="card"><h3>Verbindung ergänzen</h3><select id="relFrom"></select> → <select id="relType"><option>HEATS</option><option>SUPPLIES</option><option>CHARGES</option><option>CONNECTED_TO</option></select> → <select id="relTo"></select> <button onclick="addRelation()">Hinzufügen</button></div></section>
<section class="page"><h2>Grenzen</h2><p class="muted">Nur harte technische Grenzen und Komfortvorgaben. Diese Werte darf Learning niemals überschreiben.</p><div id="limitsEditor"></div><label class="pluginChoice"><input id="limitsConfirmed" type="checkbox" onchange="updateStart()"><span><b>Grenzen geprüft und bestätigt</b><small>Erforderlich bevor Learning / Shadow gestartet werden kann.</small></span></label></section>
<section class="page"><h2>Learning / Shadow starten</h2><div class="card"><h3>Inbetriebnahmeprüfung</h3><div id="commissioningCheck"></div><p>INS-EI speichert die Anlage lokal und startet ohne autonome Steuerhoheit.</p><button id="startButton" class="primary" onclick="save()" disabled>Anlage speichern & Learning starten</button><div id="saveResult"></div></div></section>

<div class="actions"><button id="prev" onclick="move(-1)" disabled>← Zurück</button><button id="next" class="primary" onclick="move(1)">Weiter →</button></div>
<script>
let step=0; const pages=[...document.querySelectorAll('.page')], dots=[...document.querySelectorAll('.stepDot')]; let discoveredPoints=[]; let discoveredComponents=[];
function show(){{pages.forEach((x,i)=>x.classList.toggle('active',i===step));dots.forEach((x,i)=>x.classList.toggle('active',i===step));prev.disabled=step===0;next.style.visibility=step===pages.length-1?'hidden':'visible'}}
function move(n){{step=Math.max(0,Math.min(pages.length-1,step+n));show()}}
function selectedIds(){{return [...document.querySelectorAll('[data-select-plugin]:checked')].map(x=>x.dataset.selectPlugin)}}
function syncPlugins(){{const ids=selectedIds();document.querySelectorAll('[data-config-plugin]').forEach(x=>x.hidden=!ids.includes(x.dataset.configPlugin));noneSelected.hidden=ids.length>0}}
function cfg(id){{let o={{}};document.querySelectorAll('[data-plugin="'+id+'"]').forEach(x=>{{if(x.value!=='')o[x.dataset.field]=(x.dataset.field==='port'||x.dataset.field==='unit_id')?Number(x.value):x.value}});return o}}
async function testPlugin(id){{const el=document.getElementById('r_'+id);el.textContent=' teste…';try{{const r=await fetch('setup/test-plugin',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{plugin_id:id,instance_id:id+'_main',config:cfg(id)}})}});const d=await r.json();el.className=r.ok?'ok':'bad';el.textContent=r.ok?' ✓ '+d.points.length+' Punkte':' ✗ '+(d.detail||'Fehler');if(r.ok){{discoveredPoints=discoveredPoints.filter(x=>x.plugin!==id);d.points.forEach(p=>discoveredPoints.push({{plugin:id,component:p.component_id,point:p.point}}));renderDiscovered();proposeRelations()}}}}catch(e){{el.className='bad';el.textContent=' ✗ '+e}}}}
function renderDiscovered(){{const uniq=[...new Set(discoveredPoints.map(x=>x.component))];document.getElementById('discoveredComponents').innerHTML=uniq.length?uniq.map(x=>'<div>✓ '+x+'</div>').join(''):'Noch keine Komponenten erkannt.'}}
async function save(){{const ids=selectedIds();const plugin_instances=ids.map(id=>({{id:id.replaceAll('-','_')+'_main',plugin:id,config:cfg(id)}}));const components=[...new Set(discoveredPoints.map(x=>x.component))].map(id=>({{id,kind:'GENERIC'}}));const payload={{site_id:siteId.value,timezone:timezone.value,plugin_instances,components,relations:[],connections:[],constraints:[],apps:{{}},strategy:{{modules:[]}},site_rules:[]}};const r=await fetch('setup/save',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify(payload)}});const d=await r.json();saveResult.textContent=d.saved?'Gespeichert. App jetzt neu starten.':'Fehler'}}

let relations=[];
const limitDefaults={{
 battery:[['battery_min_soc','Mindest-SOC',20,'%'],['battery_max_charge_current','Max. Ladestrom',100,'A'],['battery_max_discharge_current','Max. Entladestrom',100,'A']],
 buffer:[['buffer_max_temperature','Maximaltemperatur',75,'°C']],
 dhw:[['dhw_min_temperature','Absolute Mindesttemperatur',45,'°C'],['dhw_comfort_temperature','Komforttemperatur',55,'°C']],
 power_to_heat:[['power_to_heat_max_power','Maximale Leistung',9,'kW']]
}};
function typedMap(){{const m=new Map();discoveredComponents.filter(x=>x.ready).forEach(x=>m.set(x.id,x));return m}}
function proposeRelations(){{
 const m=typedMap(); const has=id=>m.has(id); const add=(a,b,t)=>{{if(has(a)&&has(b)&&!relations.some(x=>x.from===a&&x.to===b&&x.type===t))relations.push({{from:a,to:b,type:t}})}};
 add('pellet_boiler','buffer','HEATS');add('pellet_boiler','dhw','HEATS');add('power_to_heat','buffer','HEATS');add('buffer','hk1','SUPPLIES');add('buffer','hk2','SUPPLIES');add('grid','power_to_heat','SUPPLIES');add('pv','battery','CHARGES');add('pv','grid','CONNECTED_TO');add('battery','grid','CONNECTED_TO');
 renderTopology();renderLimits();updateStart();
}}
function renderTopology(){{const ids=[...typedMap().keys()];const opts=ids.map(x=>'<option>'+x+'</option>').join('');relFrom.innerHTML=opts;relTo.innerHTML=opts;topologyEditor.innerHTML='<div class="card">'+(relations.length?relations.map((r,i)=>'<div style="display:flex;justify-content:space-between;padding:7px 0"><span>'+r.from+' <b>→ '+r.type+' →</b> '+r.to+'</span><button onclick="removeRelation('+i+')">Entfernen</button></div>').join(''):'Noch keine Verbindungen.')+'</div>'}}
function addRelation(){{if(relFrom.value&&relTo.value&&relFrom.value!==relTo.value)relations.push({{from:relFrom.value,to:relTo.value,type:relType.value}});renderTopology();updateStart()}}
function removeRelation(i){{relations.splice(i,1);renderTopology();updateStart()}}
function renderLimits(){{const m=typedMap();let rows=[];for(const id of m.keys()){{for(const d of (limitDefaults[id]||[])){{rows.push('<div class="card"><b>'+id+'</b><br><label>'+d[1]+'</label><input type="text" data-limit-id="'+d[0]+'" data-limit-target="'+id+'" data-limit-unit="'+d[3]+'" value="'+d[2]+'"><small>'+d[3]+'</small></div>')}}limitsEditor.innerHTML=rows.length?rows.join('') :'<div class="card muted">Für die erkannten Komponenten sind noch keine Pflichtgrenzen definiert.</div>'}}
function buildConstraints(){{return [...document.querySelectorAll('[data-limit-id]')].map(x=>({{id:x.dataset.limitId,type:x.dataset.limitId.includes('min')?'MIN_VALUE':'MAX_VALUE',target:x.dataset.limitTarget,value:Number(x.value),unit:x.dataset.limitUnit}}))}}
function updateStart(){{const typed=discoveredComponents.filter(x=>x.ready).length;const unknown=discoveredComponents.filter(x=>!x.ready).length;const tested=discoveredComponents.length>0;const confirmed=document.getElementById('limitsConfirmed')?.checked||false;const ok=tested&&typed>0&&unknown===0&&confirmed;commissioningCheck.innerHTML='<div>'+(tested?'✓':'✗')+' Geräte getestet</div><div>'+(unknown===0?'✓':'✗')+' Komponenten typisiert'+(unknown?' ('+unknown+' offen)':'')+'</div><div>'+(confirmed?'✓':'✗')+' Grenzen bestätigt</div><div>✓ Autonomie: Default-Deny / Shadow</div>';startButton.disabled=!ok}}
syncPlugins();show();
</script></main></body></html>""")
