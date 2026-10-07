from ins_ei.webui import index_html
def test_shadow_navigation_button_is_rendered():
    html=index_html().body.decode()
    assert '<button data-page="shadow">Shadow</button>' in html
    assert '<section id="shadow" class="page">' in html
