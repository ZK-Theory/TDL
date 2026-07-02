import json

import pytest

from research_system.adapters.base import ProviderCommand, TransportResult
from research_system.adapters.fake import FakeTransport
from research_system.adapters.provider import ProviderAdapter
from research_system.errors import ArsError


def _command(authorized=True, segments=None):
    return ProviderCommand(
        "pcmd_" + "1" * 32,
        1,
        "a" * 64,
        "codex",
        "p0-fake",
        "implementer-v1",
        "adapter-v1",
        "b" * 64,
        "c" * 64,
        "d" * 64,
        "idem-1",
        "request_model_work",
        30.0,
        {
            "method": "fake-upper-v1",
            "raw_capacity": 100,
            "fixed_overhead": 10,
            "managed_tokens": 60,
            "reserved_variable_tokens": 5,
            "segments": segments or {"managed": "managed", "system": "reserved"},
        },
        authorized,
    )


def _result():
    return TransportResult(
        "terminal",
        json.dumps(
            {
                "provider": "codex",
                "model": "p0-fake",
                "profile_id": "implementer-v1",
                "adapter_revision": "adapter-v1",
                "command_revision": 1,
                "command_revision_hash": "a" * 64,
                "delivered_context_hash": "c" * 64,
                "response_id": "response-1",
                "output_refs": [],
            }
        ),
        "diagnostic only",
        "request-1",
        0,
    )


def test_adapter_f020_normalized_fake_receipt_is_complete():
    receipt = ProviderAdapter(["codex", "exec", "-"], FakeTransport([_result()])).issue(
        _command(), "context"
    )
    assert receipt.complete is True


def test_adapter_s013_unauthorized_command_blocks_before_transport():
    transport = FakeTransport([_result()])
    with pytest.raises(ArsError, match="unauthorized_adapter_command"):
        ProviderAdapter(["codex", "exec", "-"], transport).issue(
            _command(authorized=False), "context"
        )
    assert transport.invocations == []


def test_adapter_wrapper_unclassified_segment_blocks_issue():
    with pytest.raises(ArsError, match="wrapper_accounting_incomplete"):
        ProviderAdapter(["codex", "exec", "-"], FakeTransport([_result()])).issue(
            _command(segments={"mystery": "unclassified"}), "context"
        )
