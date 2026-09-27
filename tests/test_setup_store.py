from ins_ei.setup_store import SetupStore


def test_setup_store_persists_local_site(tmp_path):
    store = SetupStore(tmp_path)
    store.save({"api_version": "ins-ei.site/v1", "site": {"id": "home"}})
    assert store.exists()
    assert store.load()["site"]["id"] == "home"
