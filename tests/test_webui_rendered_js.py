from ins_ei.webui import index_html


def test_dashboard_uses_core_client_navigation_and_refresh():
    html = index_html().body.decode()
    for label in ("Übersicht", "Anlage", "Plugins", "Lernen", "Optimierung", "Tarife", "System"):
        assert label in html
    assert "refreshAll();setInterval(refreshAll,10000)" in html
    assert "/learning/models" in html
    assert "/strategy/evaluate" in html
