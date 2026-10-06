from ins_ei.config import TariffConfig
def test_tariff_accepts_alias_and_internal_field_names():
    a=TariffConfig.model_validate({"import":{"type":"dynamic","provider":"awattar"},"export":{"type":"dynamic"}})
    b=TariffConfig.model_validate({"import_config":{"type":"dynamic","provider":"awattar"},"export_config":{"type":"dynamic"}})
    assert a.import_config["provider"]=="awattar" and b.import_config["provider"]=="awattar"
    assert a.model_dump(by_alias=True)["import"]["provider"]=="awattar"
