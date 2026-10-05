from pathlib import Path
def test_operational_forecast_has_weather_tariffs_and_price_chart():
    f=Path("src/ins_ei/forecast_profiles.py").read_text()
    c=Path("src/ins_ei/config.py").read_text()
    t=Path("src/ins_ei/tariff_forecast.py").read_text()
    w=Path("src/ins_ei/webui.py").read_text()
    assert "cloud_cover,shortwave_radiation" in f and "HISTORICAL_PV_PLUS_WEATHER" in f
    assert "class TariffConfig" in c
    assert "market.import_price" in t and "market.export_price" in t
    assert "yPrice" in w and "Bezugspreis" in w and "Einspeisepreis" in w
