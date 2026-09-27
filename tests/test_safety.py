import pytest

from ins_ei.safety import SafetyController


def test_emergency_stop_blocks_commands_until_reset():
    safety = SafetyController()
    safety.assert_command_allowed()
    safety.engage("operator")
    with pytest.raises(RuntimeError, match="EMERGENCY_STOP_ACTIVE"):
        safety.assert_command_allowed()
    safety.release()
    safety.assert_command_allowed()
