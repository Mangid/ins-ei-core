from __future__ import annotations

from html import escape
import json
from fastapi.responses import HTMLResponse


def setup_html(plugin_items=None, version: str = "0.1.35", existing_site=None) -> HTMLResponse:
    existing_site = existing_site or {}
    existing_instances = existing_site.get('plugin_instances', [])
    instances_by_plugin = {}
    for instance in existing_instances:
        instances_by_plugin.setdefault(instance.get("plugin"), []).append(instance)
    persisted_components_json = json.dumps(existing_site.get("components", []), ensure_ascii=False)
    persisted_relations_json = json.dumps(existing_site.get("relations", []), ensure_ascii=False)
    persisted_constraints_json = json.dumps(existing_site.get("constraints", []), ensure_ascii=False)
    plugin_items = [x for x in list(plugin_items or []) if x.manifest.kind != "test"]

    choices = []
    configs = []
    for item in plugin_items:
        m = item.manifest
        pid = escape(m.id)
        plugin_existing = instances_by_plugin.get(m.id, [])
        existing = plugin_existing[0] if plugin_existing else {}
        existing_config = dict(existing.get("config", {}))
        # One-time V1 migration: legacy Victron MQTT setup -> local Modbus TCP.
        if m.id == "victron-gx" and "portal_id" in existing_config:
            existing_config.pop("portal_id", None)
            if int(existing_config.get("port", 1883)) == 1883:
                existing_config["port"] = 502
            existing_config.setdefault("battery_unit_id", 225)
            existing_config.setdefault("grid_unit_id", 30)
            existing_config.setdefault("pv_unit_ids", "22,23")
        checked = " checked" if plugin_existing else ""
        caps = " · ".join(m.capabilities)
        choices.append(
            f'<label class="pluginChoice"><input type="checkbox" data-select-plugin="{pid}"{checked} '
            f'onchange="syncPlugins()">'
            f'<span><b>{escape(m.name)}</b><small>{escape(caps)}</small></span></label>'
        )
        def render_instance(instance, index):
            instance_config = dict(instance.get("config", {}))
            if m.id == "victron-gx" and "portal_id" in instance_config:
                instance_config.pop("portal_id", None)
                if int(instance_config.get("port", 1883)) == 1883:
                    instance_config["port"] = 502
                instance_config.setdefault("battery_unit_id", 225)
                instance_config.setdefault("grid_unit_id", 30)
                instance_config.setdefault("pv_unit_ids", "22,23")
            instance_id = escape(str(instance.get("id") or f"{m.id.replace('-', '_')}_{index+1}"))
            fields = []
            for field in m.config_schema.get("fields", []):
                fid = escape(str(field.get("id", "")))
                label = escape(str(field.get("label", fid)))
                ftype = "password" if field.get("type") == "password" else "text"
                raw_value = instance_config.get(field.get("id"), field.get("default", ""))
                default = escape(str(raw_value if raw_value is not None else ""))
                fields.append(
                    f'<label>{label}</label><input data-instance="{instance_id}" data-field="{fid}" '
                    f'type="{ftype}" value="{default}">'
                )
            remove = '' if index == 0 else f'<button onclick="removePluginInstance(this)">Instanz entfernen</button>'
            return (
                f'<div class="card pluginInstance" data-plugin="{pid}" data-instance-id="{instance_id}">'
                f'<h3>{escape(m.name)} <small>{instance_id}</small></h3>'
                f'<label>Instanz-ID</label><input class="instanceId" type="text" value="{instance_id}">'
                f'{"".join(fields)}'
                f'<button onclick="testPluginInstance(this)">Verbindung testen</button> '
                f'<span class="instanceResult"></span> {remove}</div>'
            )

        rendered_instances = plugin_existing or [{"id": f"{m.id.replace('-', '_')}_main", "config": {}}]
        instance_cards = "".join(render_instance(x, i) for i, x in enumerate(rendered_instances))

        template_fields = []
        for field in m.config_schema.get("fields", []):
            fid = escape(str(field.get("id", "")))
            label = escape(str(field.get("label", fid)))
            ftype = "password" if field.get("type") == "password" else "text"
            default = escape(str(field.get("default", "") if field.get("default") is not None else ""))
            template_fields.append(
                f'<label>{label}</label><input data-field="{fid}" type="{ftype}" value="{default}">'
            )
        template = (
            f'<template data-instance-template="{pid}"><div class="card pluginInstance" data-plugin="{pid}">'
            f'<h3>{escape(m.name)} <small>neue Instanz</small></h3>'
            f'<label>Instanz-ID</label><input class="instanceId" type="text" value="">'
            f'{"".join(template_fields)}'
            f'<button onclick="testPluginInstance(this)">Verbindung testen</button> '
            f'<span class="instanceResult"></span> <button onclick="removePluginInstance(this)">Instanz entfernen</button>'
            f'</div></template>'
        )
        configs.append(
            f'<div class="pluginConfig" data-config-plugin="{pid}" hidden>'
            f'<h3>{escape(m.name)}</h3><div class="instanceList">{instance_cards}</div>'
            f'<button onclick="addPluginInstance(\'{pid}\')">+ Instanz hinzufügen</button>{template}</div>'
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
.relationRow{{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:12px 10px;border-bottom:1px solid #2b3440;border-radius:7px}}
.relationRow:nth-child(even){{background:#171d25}}
.relationRow:last-child{{border-bottom:0}}
.relationText{{min-width:0;line-height:1.45}}
.relationRemove{{flex:0 0 auto}}
</style></head><body><main>
<header><div><h1 style="margin:0">INS-EI</h1><small>V1 · v{escape(version)} · Inbetriebnahme</small></div><button onclick="history.length>1?history.back():location.href='./'">← Zurück</button></header>
<div class="steps"><span class="stepDot active">1 Grundeinstellungen</span><span class="stepDot">2 Plugins</span><span class="stepDot">3 Konfiguration</span><span class="stepDot">4 Komponenten</span><span class="stepDot">5 Anlage</span><span class="stepDot">6 Grenzen</span><span class="stepDot">7 Start</span></div>

<div class="actions" style="margin-bottom:18px"><button id="prevTop" onclick="move(-1)" disabled>← Zurück</button><button id="nextTop" class="primary" onclick="move(1)">Weiter →</button></div>
<section class="page active">
<h2>Grundeinstellungen</h2><p class="muted">Zuerst legen wir nur die Anlage selbst an.</p>
<div class="card"><label>Name / ID</label><input id="siteId" type="text" value="{escape(str(existing_site.get('site', {}).get('id', 'home-v1')))}"><label>Zeitzone</label><input id="timezone" type="text" value="{escape(str(existing_site.get('site', {}).get('timezone', 'Europe/Vienna')))}"><h3>Standort</h3><label>Ort</label><input id="locationName" type="text" value="{escape(str(existing_site.get('site', {}).get('location', {}).get('name') or ''))}"><label>PLZ</label><input id="postalCode" type="text" value="{escape(str(existing_site.get('site', {}).get('location', {}).get('postal_code') or ''))}"><label>Land</label><input id="country" type="text" value="{escape(str(existing_site.get('site', {}).get('location', {}).get('country') or 'AT'))}"><label>Breitengrad (optional)</label><input id="latitude" type="number" step="any" value="{escape('' if existing_site.get('site', {}).get('location', {}).get('latitude') is None else str(existing_site.get('site', {}).get('location', {}).get('latitude')))}"><label>Längengrad (optional)</label><input id="longitude" type="number" step="any" value="{escape('' if existing_site.get('site', {}).get('location', {}).get('longitude') is None else str(existing_site.get('site', {}).get('location', {}).get('longitude')))}"><h3>Zentrale</h3>
<label class="pluginChoice"><input id="centralEnabled" type="checkbox" {"checked" if existing_site.get("central", {}).get("enabled") else ""}><span><b>Mit INS-EI Servicezentrale verbinden</b><small>MQTT/TLS · Core funktioniert auch ohne Zentrale weiter.</small></span></label>
<label>Broker</label><input id="centralHost" type="text" value="{escape(str(existing_site.get('central', {}).get('host') or 'mqtt.ins-enertech.net'))}">
<label>Port</label><input id="centralPort" type="number" value="{escape(str(existing_site.get('central', {}).get('port') or 8883))}">
<label>Benutzer</label><input id="centralUsername" type="text" value="{escape(str(existing_site.get('central', {}).get('username') or ''))}">
<label>Passwort</label><input id="centralPassword" type="password" value="" placeholder="gespeichertes Passwort bleibt erhalten">
<label class="pluginChoice"><input id="centralTls" type="checkbox" {"checked" if existing_site.get("central", {}).get("tls", True) else ""}><span><b>TLS verwenden</b></span></label>
<button onclick="testCentral()">Verbindung testen</button> <span id="centralResult"></span></div>
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
<section class="page"><h2>Grenzen</h2><p class="muted">Nur harte technische Grenzen und Komfortvorgaben. Diese Werte darf Learning niemals überschreiben.</p><div id="limitsEditor"></div><label class="pluginChoice"><input id="limitsConfirmed" type="checkbox" onchange="updateStart()" {"checked" if existing_site.get("constraints") else ""}><span><b>Grenzen geprüft und bestätigt</b><small>Erforderlich bevor Learning / Shadow gestartet werden kann.</small></span></label></section>
<section class="page"><h2>Learning / Shadow starten</h2><div class="card"><h3>Inbetriebnahmeprüfung</h3><div id="commissioningCheck"></div><p>INS-EI speichert die Anlage lokal und startet ohne autonome Steuerhoheit.</p><button id="startButton" class="primary" onclick="save()" disabled>Konfiguration speichern</button><div id="saveResult"></div></div></section>

<div class="actions"><button id="prev" onclick="move(-1)" disabled>← Zurück</button><button id="next" class="primary" onclick="move(1)">Weiter →</button></div>
<script>
function api(path){{
  const marker='/config';
  let p=window.location.pathname;
  const i=p.lastIndexOf(marker);
  if(i>=0) p=p.slice(0,i+1);
  else if(!p.endsWith('/')) p+='/';
  return p+path.replace(/^\//,'');
}}
let step=0;
const instancePluginMap={json.dumps({x.get("id"): x.get("plugin") for x in existing_instances}, ensure_ascii=False)};
let discoveredComponents={persisted_components_json}.map(x=>({{...x,ready:true,provider:x.provider||'',plugin:instancePluginMap[x.provider]||''}}));
let relations={persisted_relations_json};
const hadPersistedTopology=relations.length>0;
const pages=[...document.querySelectorAll('.page')];
const dots=[...document.querySelectorAll('.stepDot')];
const persistedConstraints={persisted_constraints_json};
const limitDefaults={{
  battery:[['battery_min_soc','Mindest-SOC',20,'%'],['battery_max_charge_current','Max. Ladestrom',100,'A'],['battery_max_discharge_current','Max. Entladestrom',100,'A']],
  buffer:[['buffer_max_temperature','Maximaltemperatur',75,'°C']],
  dhw:[['dhw_min_temperature','Absolute Mindesttemperatur',45,'°C'],['dhw_comfort_temperature','Komforttemperatur',55,'°C']],
  power_to_heat:[['power_to_heat_max_power','Maximale Leistung',9,'kW']]
}};

function show(){{
  pages.forEach((x,i)=>x.classList.toggle('active',i===step));
  dots.forEach((x,i)=>x.classList.toggle('active',i===step));
  document.getElementById('prev').disabled=step===0;
  document.getElementById('prevTop').disabled=step===0;
  document.getElementById('next').style.visibility=step===pages.length-1?'hidden':'visible';
  document.getElementById('nextTop').style.visibility=step===pages.length-1?'hidden':'visible';
}}
function move(n){{step=Math.max(0,Math.min(pages.length-1,step+n));show();}}
function selectedIds(){{return [...document.querySelectorAll('[data-select-plugin]:checked')].map(x=>x.dataset.selectPlugin);}}
function syncPlugins(){{
  const ids=selectedIds();
  document.querySelectorAll('[data-config-plugin]').forEach(x=>x.hidden=!ids.includes(x.dataset.configPlugin));
  document.getElementById('noneSelected').hidden=ids.length>0;
}}

async function testCentral(){{
 centralResult.className='';centralResult.textContent=' teste…';
 const payload={{site_id:siteId.value,host:centralHost.value,port:Number(centralPort.value),tls:centralTls.checked,username:centralUsername.value,password:centralPassword.value}};
 try{{
  const r=await fetch(api('setup/test-central'),{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify(payload)}});
  const d=await r.json();centralResult.className=r.ok?'ok':'bad';centralResult.textContent=r.ok?' ✓ verbunden':' ✗ '+(d.detail||'Fehler');
 }}catch(e){{centralResult.className='bad';centralResult.textContent=' ✗ '+e}}
}}
function instanceConfig(card){{
  const o={{}};
  card.querySelectorAll('[data-field]').forEach(x=>{{
    if(x.value!=='') o[x.dataset.field]=(x.dataset.field==='port'||x.dataset.field.endsWith('_unit_id')||x.dataset.field==='device_id')?Number(x.value):x.value;
  }});
  return o;
}}
function normalizeInstanceId(card){{
  const input=card.querySelector('.instanceId');
  const id=input.value.trim().replace(/[^a-zA-Z0-9_-]+/g,'_');
  input.value=id;
  card.dataset.instanceId=id;
  card.querySelectorAll('[data-field]').forEach(x=>x.dataset.instance=id);
  return id;
}}
function addPluginInstance(pluginId){{
  const host=document.querySelector('[data-config-plugin="'+pluginId+'"]');
  const tpl=host.querySelector('template[data-instance-template="'+pluginId+'"]');
  const node=tpl.content.firstElementChild.cloneNode(true);
  const count=host.querySelectorAll('.pluginInstance').length+1;
  const id=pluginId.replaceAll('-','_')+'_'+count;
  node.querySelector('.instanceId').value=id; node.dataset.instanceId=id;
  node.querySelectorAll('[data-field]').forEach(x=>x.dataset.instance=id);
  host.querySelector('.instanceList').appendChild(node);
}}
function removePluginInstance(button){{button.closest('.pluginInstance').remove();}}
async function testPluginInstance(button){{
  const card=button.closest('.pluginInstance'), previousId=card.dataset.lastTestedInstanceId||card.dataset.instanceId, id=normalizeInstanceId(card), pluginId=card.dataset.plugin;
  const el=card.querySelector('.instanceResult'); el.textContent=' teste…';
  try{{
    const r=await fetch(api('setup/test-plugin'),{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{plugin_id:pluginId,instance_id:id,config:instanceConfig(card)}})}});
    const d=await r.json(); el.className=r.ok?'instanceResult ok':'instanceResult bad';
    el.textContent=r.ok?' ✓ '+d.points.length+' Punkte':' ✗ '+(d.detail||'Fehler');
    if(r.ok){{
      discoveredComponents=discoveredComponents.filter(x=>x.provider!==id&&x.provider!==previousId);
      if(previousId&&previousId!==id){{relations=relations.filter(r=>!discoveredComponents.every(x=>x.id!==r.from)&&!discoveredComponents.every(x=>x.id!==r.to));}}
      card.dataset.lastTestedInstanceId=id;
      (d.components||[]).forEach(x=>{{
        const old=discoveredComponents.find(y=>y.id===x.id);
        discoveredComponents.push({{...x,properties:(old&&old.properties)||x.properties||{{}},plugin:pluginId,provider:id}});
      }});
      renderDiscovered(); proposeRelations();
    }}
  }}catch(e){{el.className='instanceResult bad';el.textContent=' ✗ '+e;}}
}}
function typedMap(){{const m=new Map();discoveredComponents.filter(x=>x.ready).forEach(x=>m.set(x.id,x));return m;}}
function renderDiscovered(){{
  const byId=new Map(); discoveredComponents.forEach(x=>byId.set(x.id,x));
  const rows=[...byId.values()];
  document.getElementById('discoveredComponents').innerHTML=rows.length?rows.map(x=>{{
    let extra='';
    if(x.kind==='BATTERY'){{
      const p=x.properties||{{}};
      extra='<div class="card" style="margin:8px 0 14px 20px">'+
        '<label>Nennkapazität (kWh)</label><input type="number" step="0.1" data-component-prop="capacity_nominal_kwh" data-component-id="'+x.id+'" value="'+(p.capacity_nominal_kwh??'')+'">'+
      '</div>';
    }}
    if(x.kind==='PV_INPUT'){{
      const p=x.properties||{{}};
      extra='<div class="card" style="margin:8px 0 14px 20px">'+
        '<label>Bezeichnung</label><input type="text" data-pv-prop="label" data-component-id="'+x.id+'" value="'+(p.label||'')+'">'+
        '<label>Ausrichtung</label><select data-pv-prop="orientation" data-component-id="'+x.id+'">'+
          ['','SOUTH','EAST','WEST','NORTH'].map(v=>'<option value="'+v+'" '+(p.orientation===v?'selected':'')+'>'+(v||'– auswählen –')+'</option>').join('')+
        '</select>'+
        '<label>Installierte DC-Leistung (kWp)</label><input type="number" step="0.001" data-pv-prop="capacity_kwp" data-component-id="'+x.id+'" value="'+(p.capacity_kwp??'')+'">'+
      '</div>';
    }}
    return '<div class="'+(x.ready?'ok':'bad')+'">'+(x.ready?'✓ ':'⚠ ')+x.id+' → '+(x.kind||'Typ unbekannt')+'</div>'+extra;
  }}).join(''):'Noch keine Komponenten erkannt.';
  document.querySelectorAll('[data-component-prop]').forEach(el=>el.addEventListener('change',()=>{{
    const component=discoveredComponents.find(x=>x.id===el.dataset.componentId);
    if(!component)return; component.properties=component.properties||{{}};
    component.properties[el.dataset.componentProp]=el.value?Number(el.value):null;
  }}));
  document.querySelectorAll('[data-pv-prop]').forEach(el=>el.addEventListener('change',()=>{{
    const component=discoveredComponents.find(x=>x.id===el.dataset.componentId);
    if(!component)return;
    component.properties=component.properties||{{}};
    component.properties[el.dataset.pvProp]=el.dataset.pvProp==='capacity_kwp'?(el.value?Number(el.value):null):el.value;
  }}));
}}
function proposeRelations(){{
  const m=typedMap(), has=id=>m.has(id);
  // Once an installer has saved a topology, never re-add generic thermal
  // guesses that may have been deliberately removed. Only enrich it with
  // relations involving newly discovered electrical components.
  const allowThermalDefaults=!hadPersistedTopology;
  const add=(a,b,t)=>{{if(has(a)&&has(b)&&!relations.some(x=>x.from===a&&x.to===b&&x.type===t))relations.push({{from:a,to:b,type:t}});}};
  if(allowThermalDefaults){{
    add('pellet_boiler','buffer','HEATS'); add('pellet_boiler','dhw','HEATS'); add('power_to_heat','buffer','HEATS');
    add('buffer','hk1','SUPPLIES'); add('buffer','hk2','SUPPLIES'); add('grid','power_to_heat','SUPPLIES');
  }}
  [...m.values()].filter(x=>x.kind==='PV_INVERTER').forEach(x=>add(x.id,'pv','SUPPLIES'));
  add('pv','battery','CHARGES'); add('pv','grid','CONNECTED_TO'); add('battery','grid','CONNECTED_TO');
  add('grid_victron','grid','CONNECTED_TO'); add('grid_huawei','grid','CONNECTED_TO');
  renderTopology(); renderLimits(); updateStart();
}}
function relationGroup(r){{
  const s=(r.from+' '+r.to).toLowerCase();
  if(/pellet|buffer|dhw|hk|power_to_heat/.test(s)) return 1;
  if(/pv|battery/.test(s)) return 2;
  if(/grid/.test(s)) return 3;
  return 4;
}}
function renderTopology(){{
  const ids=[...typedMap().keys()], opts=ids.map(x=>'<option>'+x+'</option>').join('');
  relations.sort((a,b)=>relationGroup(a)-relationGroup(b)||(a.from+a.to).localeCompare(b.from+b.to));
  document.getElementById('relFrom').innerHTML=opts; document.getElementById('relTo').innerHTML=opts;
  document.getElementById('topologyEditor').innerHTML='<div class="card">'+(relations.length?relations.map((r,i)=>'<div class="relationRow"><span class="relationText">'+r.from+' <b>→ '+r.type+' →</b> '+r.to+'</span><button class="relationRemove" title="'+r.from+' → '+r.type+' → '+r.to+' entfernen" onclick="removeRelation('+i+')">Entfernen</button></div>').join(''):'Noch keine Verbindungen.')+'</div>';
}}
function addRelation(){{const a=relFrom.value,b=relTo.value;if(a&&b&&a!==b)relations.push({{from:a,to:b,type:relType.value}});renderTopology();updateStart();}}
function removeRelation(i){{relations.splice(i,1);renderTopology();updateStart();}}
function renderLimits(){{
  const m=typedMap(), rows=[];
  for(const id of m.keys()) for(const d of (limitDefaults[id]||[])){{
    const saved=persistedConstraints.find(x=>x.id===d[0]);
    const value=saved?saved.value:d[2];
    rows.push('<div class="card"><b>'+id+'</b><br><label>'+d[1]+'</label><input type="text" data-limit-id="'+d[0]+'" data-limit-target="'+id+'" data-limit-unit="'+d[3]+'" value="'+value+'"><small>'+d[3]+'</small></div>');
  }}
  document.getElementById('limitsEditor').innerHTML=rows.length?rows.join(''):'<div class="card muted">Für die erkannten Komponenten sind noch keine Pflichtgrenzen definiert.</div>';
}}
function buildConstraints(){{return [...document.querySelectorAll('[data-limit-id]')].map(x=>({{id:x.dataset.limitId,type:x.dataset.limitId.includes('min')?'MIN_VALUE':'MAX_VALUE',target:x.dataset.limitTarget,value:Number(x.value),unit:x.dataset.limitUnit}}));}}
function updateStart(){{
  const typed=discoveredComponents.filter(x=>x.ready).length, unknown=discoveredComponents.filter(x=>!x.ready).length, tested=discoveredComponents.length>0, confirmed=document.getElementById('limitsConfirmed')?.checked||false;
  const ok=tested&&typed>0&&unknown===0&&confirmed;
  document.getElementById('commissioningCheck').innerHTML='<div>'+(tested?'✓':'✗')+' Geräte getestet</div><div>'+(unknown===0?'✓':'✗')+' Komponenten typisiert'+(unknown?' ('+unknown+' offen)':'')+'</div><div>'+(confirmed?'✓':'✗')+' Grenzen bestätigt</div><div>✓ Autonomie: Default-Deny / Shadow</div>';
  const btn=document.getElementById('startButton');
  btn.disabled=!ok;
  if(!tested) btn.textContent='Speichern nicht möglich – Geräte testen';
  else if(unknown>0) btn.textContent='Speichern nicht möglich – Komponenten prüfen';
  else if(!confirmed) btn.textContent='Speichern nicht möglich – Grenzen bestätigen';
  else btn.textContent='Konfiguration speichern';
  const result=document.getElementById('saveResult');
  if(!ok){{
    result.className='bad';
    result.textContent='Konfiguration noch nicht speicherbar: '+(!tested?'Geräte nicht getestet.':unknown>0?'Komponententypen offen.':'Grenzen noch nicht bestätigt.');
  }} else if(!result.textContent.startsWith('✓')) {{
    result.className='ok';
    result.textContent='Bereit zum Speichern.';
  }}
}}
async function save(){{
  saveResult.className='';
  saveResult.textContent='Speichere und prüfe…';
  const ids=selectedIds();
  const plugin_instances=[];
  ids.forEach(pluginId=>{{
    document.querySelectorAll('[data-config-plugin="'+pluginId+'"] .pluginInstance').forEach(card=>{{
      const id=normalizeInstanceId(card);
      if(id) plugin_instances.push({{id,plugin:pluginId,config:instanceConfig(card)}});
    }});
  }});
  const byId=new Map(); discoveredComponents.filter(x=>x.ready).forEach(x=>byId.set(x.id,{{id:x.id,kind:x.kind,provider:x.provider||null,properties:x.properties||{{}}}}));
  const payload={{site_id:siteId.value,timezone:timezone.value,location:{{name:locationName.value||null,postal_code:postalCode.value||null,country:country.value||'AT',latitude:latitude.value?Number(latitude.value):null,longitude:longitude.value?Number(longitude.value):null}},central:{{enabled:centralEnabled.checked,host:centralHost.value,port:Number(centralPort.value),tls:centralTls.checked,username:centralUsername.value||null}},central_password:centralPassword.value,plugin_instances,components:[...byId.values()],relations,connections:[],constraints:buildConstraints(),apps:{{heating:{{enabled:true}},energy:{{enabled:true}}}},strategy:{{modules:[]}},site_rules:[],commissioning:{{status:'CONFIRMED',confirmed_at:new Date().toISOString(),confirmed_by:'installer',topology_confirmed:true,constraints_confirmed:true,notes:[]}}}};
  try{{
    const r=await fetch(api('setup/save'),{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify(payload)}});
    const text=await r.text();
    let d={{}}; try{{d=JSON.parse(text)}}catch(_e){{d={{detail:text||('HTTP '+r.status)}}}}
    if(r.ok && d.saved && d.verified){{
    saveResult.className='ok';
    saveResult.innerHTML='✓ Konfiguration dauerhaft gespeichert und geprüft.<br><small>Neustart erforderlich, damit Änderungen aktiv werden.</small>';
    }} else {{
      saveResult.className='bad';
      saveResult.textContent='✗ Speichern fehlgeschlagen: '+(d.detail||('HTTP '+r.status));
    }}
  }}catch(e){{
    saveResult.className='bad';
    saveResult.textContent='✗ Speichern fehlgeschlagen: '+e;
  }}
}}
syncPlugins(); renderDiscovered(); renderTopology(); renderLimits(); updateStart(); show();
</script></main></body></html>""")
