"""Unit tests for the per-fixture executor registry.

Task 1 registers only the F-001 control/store executor; Tasks 2-3 append
coverage for the remaining P0 cases to this module.
"""

from research_system.evals.executors import EXECUTORS, require_executor
from research_system.evals.executors.control_store import (
    CONTROL_STORE_EXECUTORS,
    execute_f001,
)

_F001_PAYLOAD = {
    "contract": "immutable_message_ownership",
    "action": {
        "operation": "publish_message",
        "slot": "task.md",
        "incoming_owner": "T0.12",
    },
}


def test_control_store_registers_f001():
    assert CONTROL_STORE_EXECUTORS == {"F-001": execute_f001}
    assert EXECUTORS["F-001"] is execute_f001
    assert require_executor("F-001") is execute_f001


def test_execute_f001_known_bad_reproduces_destructive_overwrite():
    observed = execute_f001("known_bad", _F001_PAYLOAD)
    assert observed == {
        "existing_owner": "T0.3",
        "destructive_overwrite": True,
        "surviving_ids": ["T0.12"],
    }


def test_execute_f001_known_good_preserves_both_owners():
    observed = execute_f001("known_good", _F001_PAYLOAD)
    assert observed == {
        "destructive_overwrite": False,
        "surviving_ids": ["T0.3", "T0.12"],
        "collision_visible": True,
    }
