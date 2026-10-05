from pathlib import Path
def test_validation_js_declaration_is_valid():
    s=Path("src/ins_ei/webui.py").read_text()
    assert "const t=v.totals||{};const k=(x)=>" in s
    assert "const t=v.totals||{},k=x=>" not in s
