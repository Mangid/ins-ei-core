from datetime import datetime

from ins_ei.historian import Historian
from ins_ei.models import Point, Quality, Source
from ins_ei.strategy import Confidence, Decision, Intent, Priority, Proposal


def test_historian_correlates_decision_and_command(tmp_path):
    historian = Historian(tmp_path / "history.db")
    correlation = historian.new_correlation_id()
    proposal = Proposal(
        strategy="test", action="DO", priority=Priority.OPTIMIZATION,
        reason="test reason", confidence=Confidence.HIGH,
        intents=(Intent("battery", "battery.set_charge_power", {"power_w": 1000}),),
    )
    decision = Decision(
        action="DO", reason="test reason", winning_strategy="test",
        priority=Priority.OPTIMIZATION, confidence=Confidence.HIGH,
        intents=proposal.intents, considered=(proposal,),
        decided_at=datetime.now().astimezone(),
    )
    historian.record_decision("site", decision, correlation)
    historian.record_command(
        "site", correlation, "battery", "battery.set_charge_power",
        {"power_w": 1000}, "SUCCESS", plugin_instance="battery_io",
    )
    trace = historian.correlation("site", correlation)
    assert trace["decision"]["action"] == "DO"
    assert trace["commands"][0]["status"] == "SUCCESS"


def test_historian_records_canonical_observations(tmp_path):
    historian = Historian(tmp_path / "history.db")
    point = Point(
        component_id="battery", point="battery.soc", value=80.0, unit="%",
        quality=Quality.GOOD, observed_at=datetime.now().astimezone(),
        source=Source(plugin_instance="battery_io"),
    )
    historian.record_points("site", [point], context_version="site-v1")
    with historian._connection() as db:
        row = db.execute("SELECT * FROM observations").fetchone()
    assert row["component_id"] == "battery"
    assert row["context_version"] == "site-v1"
