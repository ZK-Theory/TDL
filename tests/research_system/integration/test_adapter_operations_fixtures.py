import json

import pytest

from research_system.adapters.base import ProviderCommand, TransportResult
from research_system.adapters.fake import FakeTransport
from research_system.adapters.provider import ProviderAdapter
from research_system.errors import ArsError
from research_system.operations.coordinator import issue_prepared_dispatch
from research_system.operations.leases import artifact_disposition, runtime_disposition
from research_system.operations.recovery import (
    benchmark_disposition,
    resume_from_checkpoint,
)
from research_system.operations.resources import authorize_operational_surface
from research_system.routing.engine import PreparedDispatch


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
            "segments": segments
            or {"managed": "managed", "system": "reserved"},
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


def _checkpoint():
    return {
        "design_hash": "a",
        "code_hash": "b",
        "environment_hash": "c",
        "input_hashes": ["d"],
        "representation_hash": "e",
        "parameters_hash": "f",
        "rng_algorithm": "PCG64",
        "rng_state_hash": "g",
        "completed_work_units": [0],
        "payload_hash": "h",
    }


def test_adapter_f020_normalized_fake_receipt_is_complete():
    receipt = ProviderAdapter(
        ["codex", "exec", "-"], FakeTransport([_result()])
    ).issue(_command(), "context")
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
        ProviderAdapter(
            ["codex", "exec", "-"], FakeTransport([_result()])
        ).issue(_command(segments={"mystery": "unclassified"}), "context")


def test_f007_hidden_prerequisite_blocks_projection():
    result = benchmark_disposition(
        independent_work_units=4,
        workers=2,
        required_prerequisites={"loadings", "null_cache"},
        measured_prerequisites={"null_cache"},
        projected_runtime_s=100,
        hard_limit_s=200,
    )
    assert result["reason"] == "hidden_prerequisite"


def test_f008_invalid_worker_projection_blocks():
    result = benchmark_disposition(
        independent_work_units=1,
        workers=2,
        required_prerequisites=set(),
        measured_prerequisites=set(),
        projected_runtime_s=100,
        hard_limit_s=200,
    )
    assert result["reason"] == "invalid_worker_projection"


def test_f009_hard_runtime_guardrail_stops_operationally():
    assert runtime_disposition(elapsed_s=201, hard_limit_s=200)["status"] == (
        "stop_required"
    )


def test_f010_unauthorized_operational_expansion_blocks():
    with pytest.raises(ValueError, match="unauthorized_operational_expansion"):
        authorize_operational_surface(
            requested={"roots": {"C:/tmp", "D:/outside"}},
            granted={"roots": {"C:/tmp"}},
        )


def test_s003_late_artifact_is_preserved_without_acceptance():
    result = artifact_disposition(
        observed_at="2026-07-02T12:01:00Z",
        lease_expires_at="2026-07-02T12:00:00Z",
    )
    assert result == {
        "status": "late_artifact",
        "preserve": True,
        "acceptance_allowed": False,
    }


def test_s004_compatible_resume_creates_new_epoch():
    result = resume_from_checkpoint(_checkpoint(), _checkpoint(), prior_epoch=2)
    assert result["new_execution_epoch"] == 3
    assert result["revalidate"] == ("W3", "W4", "W5", "W6", "W7", "W8")


class _AdapterIssue:
    def __init__(self, log):
        self.log = log

    def load_evidence(self, evidence_id, content_hash):
        self.log.append("load_evidence")
        assert evidence_id == "art_" + "3" * 32
        assert content_hash == "a" * 64
        return "provider-evidence"

    def revalidate(self, route, context, provider_evidence):
        self.log.append("revalidate")
        assert route == {"kind": "selected"}
        assert context == {"context": "compiled"}
        assert provider_evidence == "provider-evidence"
        return "revalidated"

    def build_command(self, prepared, grant, lease, revalidated):
        self.log.append("build_command")
        assert prepared.state == "unissued"
        assert (grant, lease, revalidated) == ("grant", "lease", "revalidated")
        return "provider-command"

    def record_issue_command(self, provider_command):
        self.log.append("record_issue_command")
        assert provider_command == "provider-command"
        return "issue"

    def issue(self, provider_command, issued_receipt):
        self.log.append("issue")
        assert (provider_command, issued_receipt) == (
            "provider-command",
            "receipt:issue",
        )
        return "provider-receipt"


class _OperationsIssue:
    def __init__(self, log):
        self.log = log

    def build_request(self, prepared, revalidated):
        self.log.append("build_request")
        assert prepared.state == "unissued"
        assert revalidated == "revalidated"
        return "resource-request"

    def request_grant_command(self, request):
        self.log.append("request_grant_command")
        assert request == "resource-request"
        return "grant"

    def load_grant(self, grant_receipt):
        self.log.append("load_grant")
        assert grant_receipt == "receipt:grant"
        return "grant"

    def claim_lease_command(self, grant, attempt_id):
        self.log.append("claim_lease_command")
        assert grant == "grant"
        assert attempt_id == "att_" + "1" * 32
        return "lease"

    def load_lease(self, lease_receipt):
        self.log.append("load_lease")
        assert lease_receipt == "receipt:lease"
        return "lease"

    def record_provider_receipt_command(self, lease, provider_receipt):
        self.log.append("record_provider_receipt_command")
        assert (lease, provider_receipt) == ("lease", "provider-receipt")
        return "terminal"


class _CommandService:
    def __init__(self, log):
        self.log = log

    def submit(self, command):
        self.log.append(f"submit:{command}")
        return f"receipt:{command}"


def test_two_stage_issue_orders_revalidation_grant_lease_and_terminal_receipt():
    log = []
    prepared = PreparedDispatch(
        "att_" + "1" * 32,
        "asr_" + "2" * 32,
        "b" * 64,
        {"context": "compiled"},
        {"kind": "selected"},
        "art_" + "3" * 32,
        "a" * 64,
        "art_" + "4" * 32,
        "c" * 64,
        "2026-07-03T00:00:00Z",
    )
    result = issue_prepared_dispatch(
        prepared,
        _AdapterIssue(log),
        _OperationsIssue(log),
        _CommandService(log),
    )
    assert result == (
        "provider-command",
        "provider-receipt",
        "receipt:terminal",
    )
    assert log == [
        "load_evidence",
        "revalidate",
        "build_request",
        "request_grant_command",
        "submit:grant",
        "load_grant",
        "claim_lease_command",
        "submit:lease",
        "load_lease",
        "build_command",
        "record_issue_command",
        "submit:issue",
        "issue",
        "record_provider_receipt_command",
        "submit:terminal",
    ]
