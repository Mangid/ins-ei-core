import ast
from pathlib import Path


def test_setup_web_python_source_compiles():
    source = Path("src/ins_ei/setup_web.py").read_text(encoding="utf-8")
    ast.parse(source)


def test_setup_html_renders_commissioning_editor():
    from ins_ei.setup_web import setup_html
    body = setup_html([], version="test").body.decode()
    assert "Anlage & Verbindungen" in body
    assert "Grenzen geprüft und bestätigt" in body
    assert "function proposeRelations()" in body


def test_setup_wizard_has_working_navigation_contract():
    from ins_ei.setup_web import setup_html
    body = setup_html([], version="test").body.decode()
    assert 'onclick="move(1)"' in body
    assert "function move(n)" in body
    assert "function show()" in body
    assert "kind:'GENERIC'" not in body


def test_setup_restores_persisted_site_graph():
    from ins_ei.setup_web import setup_html
    site = {
        "site": {"id": "test-lab", "timezone": "Europe/Vienna"},
        "components": [{"id": "buffer", "kind": "BUFFER", "provider": "oekofen_main"}],
        "relations": [{"from": "buffer", "to": "dhw", "type": "SUPPLIES"}],
        "constraints": [{"id": "buffer_max_temperature", "type": "MAX_VALUE", "target": "buffer", "value": 78, "unit": "°C"}],
    }
    body = setup_html([], version="test", existing_site=site).body.decode()
    assert '"id": "buffer"' in body
    assert '"type": "SUPPLIES"' in body
    assert '"value": 78' in body
