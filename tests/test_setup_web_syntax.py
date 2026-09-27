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
