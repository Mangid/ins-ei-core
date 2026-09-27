from ins_ei.webui import index_html

def test_webui_contains_core_v1_surfaces():
    body = index_html().body.decode()
    assert "INS-EI" in body
    assert "/site/schema.svg" in body
    assert "/learning/models" in body
    assert "/autonomy" in body
    assert "/safety" in body
