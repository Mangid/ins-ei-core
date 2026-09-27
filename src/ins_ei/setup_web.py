from __future__ import annotations

from html import escape
from fastapi.responses import HTMLResponse


def setup_html(plugin_items=None, version: str = "0.1.5") -> HTMLResponse:
    plugin_items = list(plugin_items or [])
    cards = []
    for item in plugin_items:
        manifest = item.manifest
        if manifest.kind == "test":
            continue
        fields = []
        for field in manifest.config_schema.get("fields", []):
            fid = escape(str(field.get("id", "")))
            label = escape(str(field.get("label", fid)))
            ftype = "password" if field.get("type") == "password" else "text"
            default = escape(str(field.get("default", "")))
            fields.append(
                f'<label>{label}</label>'
                f'<input data-plugin="{escape(manifest.id)}" data-field="{fid}" '
                f'type="{ftype}" value="{default}">'
            )
        caps = " · ".join(manifest.capabilities)
        pid = escape(manifest.id)
        cards.append(
            f'<div class="card"><h3>{escape(manifest.name)}</h3>'
            f'<small>{escape(caps)}</small>'
            f'<div>{"".join(fields)}</div>'
            f'<button onclick="testPlugin(\'{pid}\')">Verbindung testen</button> '
            f'<span id="r_{pid}"></span></div>'
        )
    device_html = '<h2>2 · Geräte</h2>' + "".join(cards)
    if not cards:
        device_html += '<div class="card bad">Keine Geräte-Plugins gefunden.</div>'

    return HTMLResponse(f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>INS-EI Setup</title>
<style>body{{font-family:system-ui;background:#0b0e12;color:#eef2f6;margin:0}}main{{max-width:900px;margin:auto;padding:28px}}.card{{background:#131820;border:1px solid #29313b;border-radius:14px;padding:18px;margin:14px 0}}input{{width:100%;box-sizing:border-box;background:#0b0e12;color:white;border:1px solid #394554;border-radius:8px;padding:10px;margin:6px 0 12px}}button{{padding:10px 14px;border:0;border-radius:8px;cursor:pointer}}button.primary{{background:#e8eef6;color:#111}}small{{color:#9aa7b6}}.ok{{color:#7bd89d}}.bad{{color:#ff8585}}</style></head>
<body><main>
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px">
<div><h1 style="margin:0">INS-EI</h1><small>V1 · v{escape(version)} · Setup</small></div>
<button onclick="history.length>1?history.back():location.href='./'">← Zurück</button>
</div>
<p>Neue Anlage einrichten · Learning / Shadow</p>
<div class="card"><h3>1 · Anlage</h3><label>Name / ID</label><input id="siteId" value="home-v1"><label>Zeitzone</label><input id="timezone" value="Europe/Vienna"></div>
<div id="plugins">{device_html}</div>
<div class="card"><h3>3 · Speichern</h3><p><small>V1 speichert die Konfiguration lokal. Nach dem Speichern wird INS-EI neu gestartet und baut daraus den SiteGraph.</small></p><button class="primary" onclick="save()">Konfiguration speichern</button><div id="saveResult"></div></div>
<script>
function endpoint(path){{return new URL(path, document.baseURI).toString()}}
function cfg(id){{let o={{}};document.querySelectorAll('[data-plugin="'+id+'"]').forEach(x=>{{if(x.value!=='')o[x.dataset.field]=x.dataset.field==='port'||x.dataset.field==='unit_id'?Number(x.value):x.value}});return o}}
async function testPlugin(id){{const el=document.getElementById('r_'+id);el.textContent=' teste…';try{{const r=await fetch(endpoint('setup/test-plugin'),{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{plugin_id:id,instance_id:id+'_main',config:cfg(id)}})}});const d=await r.json();el.className=r.ok?'ok':'bad';el.textContent=r.ok?' ✓ '+d.points.length+' Punkte':' ✗ '+(d.detail||'Fehler')}}catch(e){{el.className='bad';el.textContent=' ✗ '+e}}}}
async function save(){{const ids=[...new Set([...document.querySelectorAll('[data-plugin]')].map(x=>x.dataset.plugin))];const plugin_instances=ids.filter(id=>Object.keys(cfg(id)).length).map(id=>({{id:id.replaceAll('-','_')+'_main',plugin:id,config:cfg(id)}}));const payload={{site_id:siteId.value,timezone:timezone.value,plugin_instances,components:[],relations:[],connections:[],constraints:[],apps:{{}},strategy:{{modules:[]}},site_rules:[]}};const r=await fetch(endpoint('setup/save'),{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify(payload)}});const d=await r.json();saveResult.textContent=d.saved?'Gespeichert. INS-EI neu starten.':'Fehler'}}
</script></main></body></html>""")
