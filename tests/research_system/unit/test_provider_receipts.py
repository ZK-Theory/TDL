from dataclasses import asdict
import json

import pytest

from research_system.adapters.base import ProviderCommand, TransportResult
from research_system.adapters.fake import FakeTransport
from research_system.adapters.provider import (
    ProviderAdapter,
    default_provider_operation_policy,
    normalize_receipt,
)
from research_system.errors import ArsError


def _command(**changes):
    values = {
        "provider_command_id": "pcmd_" + "1" * 32,
        "revision": 2,
        "revision_hash": "a" * 64,
        "provider": "codex",
        "model": "p0-fake",
        "profile_id": "implementer-v1",
        "adapter_revision": "codex-adapter-v1",
        "policy_hash": "b" * 64,
        "context_hash": "c" * 64,
        "rendered_payload_hash": "d" * 64,
        "idempotency_key": "idem-1",
        "operation": "request_model_work",
        "timeout_s": 30.0,
        "wrapper_accounting": {
            "method": "fake-upper-v1",
            "raw_capacity": 100,
            "fixed_overhead": 10,
            "managed_tokens": 60,
            "reserved_variable_tokens": 5,
            "segments": {"managed": "managed", "system": "reserved"},
        },
        "authorized": True,
    }
    values.update(changes)
    return ProviderCommand(**values)


def _terminal_payload(**changes):
    payload = {
        "provider": "codex",
        "model": "p0-fake",
        "profile_id": "implementer-v1",
        "adapter_revision": "codex-adapter-v1",
        "command_revision": 2,
        "command_revision_hash": "a" * 64,
        "delivered_context_hash": "c" * 64,
        "response_id": "response-1",
        "output_refs": ["art_" + "2" * 32],
    }
    payload.update(changes)
    return json.dumps(payload)


def test_exact_command_revision_mismatch_is_incomplete():
    result = TransportResult("terminal", _terminal_payload(command_revision=1), "", None, 0)
    receipt = normalize_receipt(_command(), result)
    assert receipt.status == "incomplete"
    assert receipt.failure_code == "provider_completion_unproven"


def test_timeout_is_uncertain_not_success():
    result = TransportResult("timed_out", "", "timeout details", None, None)
    receipt = normalize_receipt(_command(), result)
    assert receipt.status == "uncertain"
    assert receipt.complete is False


def test_duplicate_and_cancellation_remain_explicit():
    duplicate = normalize_receipt(
        _command(),
        TransportResult("duplicate", _terminal_payload(), "", "request-1", 0),
    )
    cancelled = normalize_receipt(
        _command(), TransportResult("cancelled", "", "", "request-1", None)
    )
    assert duplicate.status == "duplicate"
    assert duplicate.complete is True
    assert cancelled.status == "cancelled"
    assert cancelled.complete is False


def test_unclassified_wrapper_accounting_blocks_issue():
    command = _command(
        wrapper_accounting={
            "method": "fake-upper-v1",
            "raw_capacity": 100,
            "fixed_overhead": 10,
            "managed_tokens": 60,
            "reserved_variable_tokens": 5,
            "segments": {"unknown": "unclassified"},
        }
    )
    with pytest.raises(ArsError, match="wrapper_accounting_incomplete"):
        normalize_receipt(
            command, TransportResult("terminal", _terminal_payload(), "", None, 0)
        )


def test_unauthorized_adapter_command_never_invokes_transport():
    transport = FakeTransport(
        [TransportResult("terminal", _terminal_payload(), "", None, 0)]
    )
    adapter = ProviderAdapter(["codex", "exec", "-"], transport)
    with pytest.raises(ArsError, match="unauthorized_adapter_command"):
        adapter.issue(_command(authorized=False), "managed context")
    assert transport.invocations == []


def test_authorized_undeclared_shell_never_invokes_transport():
    transport = FakeTransport(
        [TransportResult("terminal", _terminal_payload(), "", None, 0)]
    )
    adapter = ProviderAdapter(["codex", "exec", "-"], transport)
    with pytest.raises(ArsError, match="undeclared_adapter_operation"):
        adapter.issue(_command(operation="undeclared_shell", authorized=True), "managed context")
    assert transport.invocations == []


def test_live_enablement_cannot_be_attached_to_a_non_fake_transport():
    class TrapTransport:
        def invoke(self, argv, stdin, timeout_s):  # pragma: no cover - must never run
            raise AssertionError((argv, stdin, timeout_s))

    with pytest.raises(ArsError, match="live_provider_capability_not_implemented"):
        ProviderAdapter(
            ["provider"],
            TrapTransport(),
            operation_policy=default_provider_operation_policy(
                live_provider_enabled=True
            ),
        )


def test_normalized_receipt_excludes_raw_transcripts():
    secret = "raw transcript must not persist"
    receipt = normalize_receipt(
        _command(),
        TransportResult("terminal", _terminal_payload(), secret, "request-1", 0),
    )
    serialized = json.dumps(asdict(receipt), sort_keys=True)
    assert receipt.complete is True
    assert secret not in serialized
    assert "stdout" not in serialized
    assert "stderr" not in serialized


def test_provider_outage_normalizes_to_incomplete_typed_receipt_without_output():
    transport = FakeTransport(
        [TransportResult("provider_unavailable", "", "synthetic outage", None, None)]
    )
    receipt = ProviderAdapter(
        ["fake-provider"],
        transport,
        operation_policy=default_provider_operation_policy(live_provider_enabled=True),
    ).issue(
        _command(), "managed context"
    )
    assert receipt.status == "incomplete"
    assert receipt.complete is False
    assert receipt.failure_code == "provider_unavailable"
    assert receipt.output_refs == ()
    assert receipt.output_hash is None
