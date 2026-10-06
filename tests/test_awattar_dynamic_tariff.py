from pathlib import Path
def test_awattar_dynamic_tariff_contract():
    t=Path("src/ins_ei/tariff_forecast.py").read_text();w=Path("src/ins_ei/webui.py").read_text()
    assert "https://api.awattar.at/v1/marketdata" in t
    assert "(epex+surcharge)*(1+vat/100)" in t
    assert "epex-(abs(epex)*fee/100)" in t
    assert "market.import_price" in t and "market.export_price" in t
    assert "tariffActive" in w and "tariffPriceInfo" in w
