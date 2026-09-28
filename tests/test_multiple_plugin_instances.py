from ins_ei.config import SiteConfig


def test_site_accepts_multiple_instances_of_same_plugin():
    site = SiteConfig.model_validate({
        "api_version": "ins-ei.site/v1",
        "site": {"id": "multi"},
        "plugin_instances": [
            {"id": "fronius_1", "plugin": "fronius", "config": {"host": "10.0.0.1"}},
            {"id": "fronius_2", "plugin": "fronius", "config": {"host": "10.0.0.2"}},
        ],
    })
    assert [x.id for x in site.plugin_instances] == ["fronius_1", "fronius_2"]
    assert all(x.plugin == "fronius" for x in site.plugin_instances)
