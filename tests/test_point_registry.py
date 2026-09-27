from ins_ei.point_registry import definition, validate_point


def test_fast_grid_power_has_short_freshness():
    assert definition("grid.export_power").stale_after_seconds == 10


def test_thermal_temperature_is_slower():
    assert definition("thermal.temperature_upper").stale_after_seconds > definition("grid.export_power").stale_after_seconds


def test_registry_validates_units_and_types():
    assert validate_point("grid.import_power", 1234, "W") == []
    assert validate_point("grid.import_power", "1234", "W")
    assert validate_point("grid.import_power", 1234, "kW")
    assert validate_point("vendor.secret", 1, None) == ["POINT_UNKNOWN:vendor.secret"]
