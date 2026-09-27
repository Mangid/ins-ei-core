import json

from ins_ei.audit import AuditLog


def test_audit_writes_jsonl(tmp_path):
    path = tmp_path / "audit.jsonl"
    audit = AuditLog("site-a", path)
    audit.record("strategy.decision", action="HOLD")
    data = json.loads(path.read_text(encoding="utf-8").strip())
    assert data["event"] == "strategy.decision"
    assert data["site"] == "site-a"
    assert data["data"]["action"] == "HOLD"
