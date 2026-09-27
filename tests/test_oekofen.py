from ins_ei.plugins.oekofen import OekofenPlugin


def test_oekofen_normalizes_realistic_all_payload():
    plugin = OekofenPlugin("oekofen_main", {
        "host": "127.0.0.1",
        "password": "x",
        "components": {"boiler": "boiler", "buffer": "buf", "dhw": "water"},
    })
    payload = {
        "pe1": {
            "L_temp_act": {"val": 685},
            "L_modulation": {"val": 43},
            "L_statetext": {"val": "Heizen"},
            "mode": {"val": 1},
            "unknown_future_key": {"val": 123},
        },
        "pu1": {"L_tpo_act": {"val": 612}, "L_tpm_act": {"val": 488}},
        "ww1": {"L_ontemp_act": {"val": 551}, "heat_once": {"val": False}},
    }

    points, used = plugin._normalize(payload)
    values = {(p.component_id, p.point): p.value for p in points}

    assert values[("boiler", "thermal.temperature")] == 68.5
    assert values[("boiler", "power.modulation")] == 43.0
    assert values[("buf", "thermal.temperature_upper")] == 61.2
    assert values[("water", "thermal.temperature")] == 55.1
    assert ("pe1", "unknown_future_key") not in used


def test_oekofen_commands_are_canonical(monkeypatch):
    plugin = OekofenPlugin("oekofen_main", {"host": "127.0.0.1", "password": "x"})
    plugin.start()
    calls = []
    monkeypatch.setattr(plugin.transport, "set_value", lambda s, v, x: calls.append((s, v, x)) or "OK")

    plugin.execute("dhw.request_once", {"enabled": True})
    plugin.execute("heat_generator.set_enabled", {"enabled": False})

    assert calls == [("ww1", "heat_once", "true"), ("pe1", "mode", 0)]
