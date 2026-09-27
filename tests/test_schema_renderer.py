from ins_ei.schema_renderer import render_svg


def test_renderer_uses_canonical_component_semantics():
    view = {
        "site": "test",
        "components": [
            {
                "id": "boiler",
                "kind": "HEAT_GENERATOR",
                "presentation": {"role": "source", "shape": "heat_generator", "orientation": "horizontal"},
                "ports": [], "sensors": [], "points": [],
            },
            {
                "id": "buffer",
                "kind": "BUFFER",
                "presentation": {"role": "storage", "shape": "tank", "orientation": "vertical"},
                "ports": [],
                "sensors": [{"id": "top", "position": 0.1, "value": {"value": 65, "unit": "°C"}}],
                "points": [],
            },
        ],
        "connections": [{"from": "boiler.supply", "to": "buffer.middle", "medium": "WATER"}],
    }
    svg = render_svg(view)
    assert "<svg" in svg
    assert "boiler" in svg
    assert "buffer" in svg
    assert "65 °C" in svg
    assert "boiler.supply" in svg
