import json

import pytest

from research_system.adapters.base import ProviderCommand, TransportResult
from research_system.adapters.fake import FakeTransport
from research_system.adapters.provider import ProviderAdapter, default_provider_operation_policy
from research_system.errors import ArsError
from research_system.operations.leases import artifact_disposition, runtime_disposition
from research_system.operations.recovery import (
    benchmark_disposition,
    resume_from_checkpoint,
)
from research_system.operations.resources import authorize_operational_surface


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
        ["codex", "exec", "-"],
        FakeTransport([_result()]),
        operation_policy=default_provider_operation_policy(live_provider_enabled=True),
    ).issue(_command(), "context")
    assert receipt.complete is True


def test_adapter_s013_unauthorized_command_blocks_before_transport():
    transport = FakeTransport([_result()])
    with pytest.raises(ArsError, match="unauthorized_adapter_command"):
        ProviderAdapter(["codex", "exec", "-"], transport).issue(_command(authorized=False), "context")
    assert transport.invocations == []


def test_adapter_wrapper_unclassified_segment_blocks_issue():
    with pytest.raises(ArsError, match="wrapper_accounting_incomplete"):
        ProviderAdapter(
            ["codex", "exec", "-"],
            FakeTransport([_result()]),
            operation_policy=default_provider_operation_policy(live_provider_enabled=True),
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
    assert runtime_disposition(elapsed_s=201, hard_limit_s=200)["status"] == ("stop_required")


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
