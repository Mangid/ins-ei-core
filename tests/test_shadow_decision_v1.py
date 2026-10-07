from pathlib import Path
def test_shadow_decision_v1_is_observe_only_and_explainable():
    s=Path("src/ins_ei/shadow_decision.py").read_text();r=Path("src/ins_ei/runtime.py").read_text();a=Path("src/ins_ei/api.py").read_text();w=Path("src/ins_ei/webui.py").read_text()
    assert '"mode":"OBSERVE_ONLY"' in s
    for x in ("battery","thermal","heat_source","reason"): assert x in s
    assert "shadow_decision" in r and '"/shadow/decisions"' in a
    assert "Shadow Decision" in w and "schaltet aber nichts" in w
    assert "SOC %" in w and "display:true" in w
