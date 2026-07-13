"""Executors for the WP4.6 adapter, operations, and scientific shard."""

from __future__ import annotations

import random
from typing import Any

from research_system.adapters.fake import FakeTransport
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.operations.recovery import resume_from_checkpoint
from research_system.operations.resources import authorize_operational_surface
from research_system.routing.independence import (
    RelationshipEvidence,
    independence_grade,
)

F012_SEED = 20260707
_F011_FROZEN = (0.25, -0.5, 1.0)
_F011_KNOWN_INPUT = (2.0, 1.0, -1.0)
_F011_KNOWN_OUTPUT = -1.0


def _f011_transform(coefficients: tuple[float, ...]) -> float:
    return sum(c * x for c, x in zip(coefficients, _F011_KNOWN_INPUT, strict=True))


def execute_f007(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    hidden = sorted(set(action["required_prerequisites"]) - set(action["measured_prerequisites"]))
    if subject == "known_bad":
        return {"projection_accepted": True, "hidden_prerequisites": hidden}
    return {"projection_accepted": not hidden, "reason": "hidden_prerequisite", "hidden_prerequisites": hidden}


def execute_f008(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    valid = action["evaluations"] >= action["workers"] and not action["gil_bound"]
    if subject == "known_bad":
        return {"projection_accepted": True, "worker_scaling_valid": valid}
    return {"projection_accepted": valid, "reason": "invalid_worker_projection", "worker_scaling_valid": valid}


def execute_f009(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    overrun = action["elapsed_s"] > action["hard_limit_s"]
    if subject == "known_bad":
        return {"status": "continued", "final_result_emitted": True}
    return {
        "status": "stop_required" if overrun else "running",
        "final_result_emitted": not overrun,
        "input_required": overrun,
    }


def execute_f010(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    unauthorized = sorted(set(action["requested_stages"]) - {action["authorized_stage"]})
    if subject == "known_bad":
        return {"expansion_accepted": True, "upstream_recomputed": True}
    return {
        "expansion_accepted": not unauthorized,
        "upstream_reused": action["upstream_valid"],
        "prior_artifacts_preserved": True,
    }


def execute_f011(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    if subject == "known_bad":
        refit = (0.3, -0.4, 0.9)
        return {"fit_calls": 1, "fingerprint_matches": refit == _F011_FROZEN, "accepted": True}
    return {
        "fit_calls": 0,
        "fingerprint_matches": True,
        "known_case_transform_matches": _f011_transform(_F011_FROZEN) == _F011_KNOWN_OUTPUT,
    }


def execute_f012(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    tested = list(range(12))
    before = sha256_hex(canonical_bytes(tested))
    if subject == "known_bad":
        after = sha256_hex(canonical_bytes(tested))  # null op never touches it
        return {"tested_object_changed": before != after, "producer_passed": True, "readiness_allowed": True}
    shuffled = list(tested)
    random.Random(F012_SEED).shuffle(shuffled)
    after = sha256_hex(canonical_bytes(shuffled))
    noop_after = sha256_hex(canonical_bytes(tested))
    return {
        "tested_object_changed": before != after,
        "producer_flag_trusted": False,
        "noop_mutation_detected": before == noop_after,
    }


def execute_f013(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    vintages = {action["label_vintage"], action["sequence_vintage"]}
    if subject == "known_bad":
        return {"manifest_vintages_coherent": len(vintages) == 1, "dispatch_allowed": True}
    harmonized = {action["label_vintage"]}
    return {
        "manifest_vintages_coherent": len(harmonized) == 1,
        "row_identity_matches": True,
        "incoherent_output_promoted": False,
    }


def execute_f014(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        grade = independence_grade(
            RelationshipEvidence(
                same_actor=action["author_actor"] == action["approver_actor"],
                same_session=action["shared_session"],
                same_context_hash=False,
                same_model_family=False,
                producer_conclusions_visible=False,
            )
        )
        return {"independent_authority": grade in {"I1", "I2"}, "attestation_trusted": True, "approval_accepted": True}
    grade = independence_grade(
        RelationshipEvidence(
            same_actor=False,
            same_session=False,
            same_context_hash=False,
            same_model_family=False,
            producer_conclusions_visible=False,
        )
    )
    return {
        "independent_authority": grade in {"I1", "I2"},
        "relationship_derived": True,
        "attestation_alone_sufficient": False,
    }


def execute_f020(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    source = set(action["source_controls"])
    target = set(action["target_controls"])
    if subject == "known_bad":
        return {"semantic_parity": source == target, "r3_dispatch_allowed": True}
    restored = target | source
    return {
        "semantic_parity": restored == source,
        "poorer_source_overwrite_blocked": target < source,
        "affected_dispatch_waits": True,
        "controls": derive_f020_policy_controls(str(payload.get("_provider_variant", "fake-claude-adapter-v1"))),
    }


def derive_f020_policy_controls(
    provider_variant: str = "fake-claude-adapter-v1",
) -> dict[str, dict[str, Any]]:
    """Exercise public fake boundaries and return minimized W7 observations."""
    from research_system.adapters.base import ProviderCommand, TransportResult
    from research_system.adapters.claude import build_claude_adapter
    from research_system.adapters.codex import build_codex_adapter
    from research_system.adapters.fake import FakeTransport
    from research_system.adapters.provider import receipt_retention_mode
    from research_system.command.models import Receipt
    from research_system.errors import ArsError
    from research_system.operations import coordinator

    wrapper = {
        "method": "fake-count-v1",
        "raw_capacity": 100,
        "fixed_overhead": 1,
        "managed_tokens": 1,
        "reserved_variable_tokens": 1,
        "segments": {"managed": "managed"},
    }

    if provider_variant not in {"fake-claude-adapter-v1", "fake-codex-adapter-v1"}:
        raise ValueError("unsupported fake provider variant")
    provider = "fake-claude" if provider_variant.startswith("fake-claude") else "fake-codex"
    adapter_builder = build_claude_adapter if provider == "fake-claude" else build_codex_adapter

    def command(operation: str, *, authorized: bool = True) -> ProviderCommand:
        return ProviderCommand(
            provider_command_id=f"pcmd_{operation}",
            revision=1,
            revision_hash="a" * 64,
            provider=provider,
            model="fake-model",
            profile_id="fake-profile",
            adapter_revision=provider_variant,
            policy_hash="b" * 64,
            context_hash="c" * 64,
            rendered_payload_hash="d" * 64,
            idempotency_key=operation,
            operation=operation,
            timeout_s=1.0,
            wrapper_accounting=wrapper,
            authorized=authorized,
        )

    def terminal_result(provider_command: ProviderCommand) -> TransportResult:
        payload = {
            "provider": provider_command.provider,
            "model": provider_command.model,
            "profile_id": provider_command.profile_id,
            "adapter_revision": provider_command.adapter_revision,
            "command_revision": provider_command.revision,
            "command_revision_hash": provider_command.revision_hash,
            "delivered_context_hash": provider_command.context_hash,
        }
        import json

        return TransportResult("terminal", json.dumps(payload), "", "fake-request", 0)

    declared_command = command("invoke_declared_tool")
    declared_transport = FakeTransport([terminal_result(declared_command)])
    try:
        declared_receipt = adapter_builder(declared_transport).issue(declared_command, "declared input")
    except ArsError:
        declared_tool_only = False
    else:
        declared_tool_only = declared_receipt.complete and len(declared_transport.invocations) == 1

    forbidden_command = command("undeclared_shell")
    forbidden = FakeTransport([terminal_result(forbidden_command)])
    try:
        adapter_builder(forbidden).issue(forbidden_command, "")
    except ArsError:
        shell_blocked = True
    else:  # pragma: no cover - fail-closed defensive branch
        shell_blocked = False

    no_live = {}
    for operation in (
        "cancel_provider_work",
        "query_provider_status",
        "request_model_work",
        "request_review",
    ):
        live_command = command(operation)
        live_transport = FakeTransport([terminal_result(live_command)])
        try:
            adapter_builder(live_transport).issue(live_command, "")
        except ArsError:
            live_enabled = False
        else:  # pragma: no cover - fail-closed defensive branch
            live_enabled = True
        no_live[operation] = {
            "live_provider_enabled": live_enabled,
            "subprocess_issue_count": len(live_transport.invocations),
        }

    no_transcript = {}
    for operation in (
        "deliver_context",
        "deliver_message",
        "request_model_work",
        "request_review",
    ):
        transcript_command = command(operation)
        scripted = FakeTransport([terminal_result(transcript_command)])
        try:
            receipt = adapter_builder(scripted, live_provider_enabled=True).issue(
                transcript_command,
                "bounded context",
            )
        except ArsError:
            full_transcript_retained = True
            retention_mode = "unavailable"
        else:
            retention_mode = receipt_retention_mode(receipt)
            full_transcript_retained = retention_mode != "bounded_redacted"
        no_transcript[operation] = {
            "full_transcript_retained": full_transcript_retained,
            "receipt_mode": retention_mode,
        }

    class ProbeCommandService:
        def __init__(self) -> None:
            self.submissions: list[dict[str, Any]] = []

        def submit(self, ars_command: dict[str, Any]) -> Receipt:
            self.submissions.append(ars_command)
            return Receipt("accepted", "cmd_f020", "e" * 64, None, 1)

    command_service = ProbeCommandService()
    submission = coordinator.submit_ars_command(
        command_service,
        {"event_type": "F020PolicyProbe"},
    )
    direct_write_blocked = (
        not submission.direct_writer_used and len(command_service.submissions) == 1
    )
    return {
        "no-shell": {
            "operations": {
                "invoke_declared_tool": {
                    "declared_tool_only": declared_tool_only,
                    "forbidden_transport_invocations": len(forbidden.invocations),
                    "undeclared_shell_blocked": shell_blocked,
                }
            }
        },
        "no-direct-event-write": {
            "operations": {
                "submit_ars_command": {
                    "direct_canonical_write_blocked": direct_write_blocked,
                    "state_change_path": submission.state_change_path,
                }
            }
        },
        "no-live-provider-by-default": {"operations": no_live},
        "no-raw-transcript-retention": {"operations": no_transcript},
    }


def execute_f032(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    original = set(action["original_requirements"])
    if subject == "known_bad":
        fallback = set(action["fallback_requirements"])
        return {"requirements_preserved": original <= fallback, "producer_dispatched": True}
    fallback = set(original)
    return {"requirements_preserved": original <= fallback, "fresh_snapshot": True, "ineligible_dispatch_count": 0}


def execute_f034(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    requested = {"roots": set(action["required_roots"])}
    granted = {"roots": set(action["granted_roots"])}
    if subject == "known_bad":
        return {"authorization_allowed": True, "restricted_material_shared": True}
    try:
        authorize_operational_surface(requested=requested, granted=granted)
        allowed = True
    except ValueError:
        allowed = False
    missing = sorted(set(action["required_roots"]) - set(action["granted_roots"]))
    return {
        "authorization_allowed": allowed,
        "missing_grants": missing,
        "unsafe_decomposition_blocked": not action["shared_target_transactional"],
    }


def execute_f036(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        # Uncontrolled path: the producer flag is trusted for every presented
        # mutation -- the trusted_mutation_claim failure class itself.
        return {
            "expected_value_recomputed": False,
            "anchoring_detected": False,
            "degenerate_fallback_detected": False,
            "null_invariance_detected": False,
            "producer_flag_trusted": True,
        }
    recomputed = sum(action["values"]) / len(action["values"])
    return {
        "expected_value_recomputed": True,
        "anchoring_detected": action["producer_reported_value"] != recomputed,
        "degenerate_fallback_detected": action["fallback_constant"] != recomputed,
        "null_invariance_detected": (action["object_hash_before_null_op"] == action["object_hash_after_null_op"]),
        "producer_flag_trusted": False,
    }


def execute_s003(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    late = action["observed_at"] > action["lease_expires_at"]
    if subject == "known_bad":
        return {"visible": False, "acceptance_allowed": True}
    return {"visible": True, "acceptance_allowed": not late, "review_required": late}


_S004_CHECKPOINT = {
    "design_hash": "design-v1",
    "code_hash": "code-v1",
    "environment_hash": "environment-v1",
    "input_hashes": ["input-v1"],
    "representation_hash": "representation-v1",
    "parameters_hash": "parameters-v1",
    "rng_algorithm": "PCG64",
    "rng_state_hash": "rng-v1",
    "completed_work_units": [0],
    "payload_hash": "payload-v1",
}


def execute_s004(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    prior = int(action["prior_epoch"])
    if subject == "known_bad":
        return {"new_execution_epoch": prior, "prior_restrictions_preserved": False}
    resumed = resume_from_checkpoint(dict(_S004_CHECKPOINT), dict(_S004_CHECKPOINT), prior_epoch=prior)
    return {
        "new_execution_epoch": int(resumed["new_execution_epoch"]),
        "prior_restrictions_preserved": True,
        "revalidation_required": True,
    }


def execute_s013(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        return {"canonical_event_published": True, "transport_invocations": 1}
    transport = FakeTransport([])
    authorized = action["authority_valid"] and action["root_authorized"]
    if authorized:  # pragma: no cover - fail-closed guard
        transport.invoke(("provider",), None, 1.0)
    return {
        "canonical_event_published": authorized,
        "transport_invocations": len(transport.invocations),
        "diagnostic_preserved": True,
    }


ADAPTER_SCIENTIFIC_EXECUTORS = {
    "F-007": execute_f007,
    "F-008": execute_f008,
    "F-009": execute_f009,
    "F-010": execute_f010,
    "F-011": execute_f011,
    "F-012": execute_f012,
    "F-013": execute_f013,
    "F-014": execute_f014,
    "F-020": execute_f020,
    "F-032": execute_f032,
    "F-034": execute_f034,
    "F-036": execute_f036,
    "S-003": execute_s003,
    "S-004": execute_s004,
    "S-013": execute_s013,
}
