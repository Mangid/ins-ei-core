from ins_ei.webui import index_html


def test_dashboard_uses_safe_model_row_event_binding():
    html = index_html().body.decode()
    assert 'data-model-id="' in html
    assert "querySelectorAll('[data-model-id]')" in html
    assert 'onclick="showModel(' not in html
    assert "refresh(); setInterval(refresh,10000)" in html
