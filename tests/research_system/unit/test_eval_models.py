from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from research_system.errors import SchemaError
from research_system.evals.models import (
    CoverageManifest,
    EvaluationRun,
    FixtureDefinition,
    GraderRequirement,
    GraderResult,
    ReleaseGateDecision,
)
from research_system.schema_registry import SchemaRegistry


UUID7 = "01978abc-0001-7000-8000-000000000001"
SCHEMAS = Path(".research-system/schemas")


def _grader_requirement(**changes: object) -> GraderRequirement:
    values = {
        "grader_id": "state",
        "grader_class": "D",
        "grader_version": "v1",
        "critical": True,
        "required": True,
        "independence_requirement": "deterministic_independent",
        "evidence_selectors": ("command_receipt",),
    }
    values.update(changes)
    return GraderRequirement(**values)


def _fixture(**changes: object) -> FixtureDefinition:
    values = {
        "fixture_id": "F-001",
        "fixture_revision": "r1",
        "title": "Single-slot overwrite",
        "owner": "evaluation_owner",
        "status": "authored",
        "incident_basis": "historical",
        "input_fidelity": "reconstructed",
        "risk_tier": "R2",
        "assurance_lanes": ("provenance",),
        "failure_class": "authority_overwrite",
        "priority": "P0",
        "gate_stage": "p0_materialization",
        "source_manifest_hash": "a" * 64,
        "decision_refs": ("P-030",),
        "policy_versions": ("canonical-policy-v1",),
        "schema_versions": ("fixture-definition-v1",),
        "confidentiality": "internal",
        "permitted_consumers": ("eval",),
        "setup_hash": "b" * 64,
        "stimulus_hash": "c" * 64,
        "pre_control_oracle_hash": "d" * 64,
        "post_control_oracle_hash": "e" * 64,
        "required_trajectory": ("two_messages_survive",),
        "forbidden_trajectory": ("overwrite",),
        "allowed_terminal_states": ("decided",),
        "expected_stop_semantics": "none",
        "required_graders": (_grader_requirement(),),
        "threshold_policy_ids": ("tp-1",),
        "required_evidence_classes": ("command_receipt",),
        "known_bad_reference_hash": "f" * 64,
        "known_good_reference_hash": "0" * 64,
        "mutation_ids": ("overwrite",),
        "safe_variation_ids": ("message_order",),
        "calibration_record_id": None,
        "retention_class": "R0",
        "retention_rule_id": "retain-with-decision",
        "redaction_policy_id": "redaction-v1",
    }
    values.update(changes)
    return FixtureDefinition(**values)


def _run(**changes: object) -> EvaluationRun:
    values = {
        "evaluation_run_id": f"run_{UUID7}",
        "fixture_id": "F-001",
        "fixture_revision": "r1",
        "subject_type": "candidate",
        "subject_version": "candidate-v1",
        "subject_hash": "a" * 64,
        "run_role": "candidate",
        "attempt_number": 1,
        "coverage_manifest_id": f"cvm_{UUID7}",
        "policy_bundle_hash": "b" * 64,
        "provider_variant": "none",
        "runtime_variant": "python-3.13-windows",
        "state": "declared",
    }
    values.update(changes)
    return EvaluationRun(**values)


def _release_decision(**changes: object) -> ReleaseGateDecision:
    values = {
        "release_gate_decision_id": f"rgd_{UUID7}",
        "coverage_manifest_id": f"cvm_{UUID7}",
        "baseline_identity": "main",
        "candidate_identity": "wp4",
        "evidence_snapshot_hash": "f" * 64,
        "required_verdicts": (),
        "critical_failures": (),
        "parity_status": "pass",
        "operations_status": "pass",
        "decision": "pass",
        "decided_at": "2026-07-03T12:00:00Z",
        "canonical_event_ref": f"evt_{UUID7}",
    }
    values.update(changes)
    return ReleaseGateDecision(**values)


def test_fixture_keeps_priority_and_gate_stage_independent():
    fixture = _fixture(priority="P1", gate_stage="p0_materialization")
    assert (fixture.priority, fixture.gate_stage) == ("P1", "p0_materialization")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("priority", "implementation_convenience", "invalid priority"),
        ("gate_stage", "gate3_spec_review", "invalid gate_stage"),
        ("retention_class", "R3", "prohibited retention_class"),
    ],
)
def test_fixture_rejects_open_or_prohibited_enums(field, value, message):
    with pytest.raises(ValueError, match=message):
        _fixture(**{field: value})


def test_grader_requirement_requires_explicit_evidence_selectors():
    with pytest.raises(ValueError, match="evidence_selectors must not be empty"):
        _grader_requirement(evidence_selectors=())


def test_fixture_and_nested_grader_contracts_are_immutable():
    fixture = _fixture()
    with pytest.raises(FrozenInstanceError):
        fixture.priority = "P1"
    with pytest.raises(FrozenInstanceError):
        fixture.required_graders[0].critical = False


def test_grader_verdict_and_class_are_closed_enums():
    values = {
        "grader_result_id": f"grr_{UUID7}",
        "evaluation_run_id": f"run_{UUID7}",
        "fixture_id": "F-001",
        "fixture_revision": "r1",
        "grader_id": "state",
        "grader_class": "D",
        "grader_version": "v1",
        "verdict": "pass",
        "severity": "critical",
        "critical": True,
        "required": True,
        "subject_hash": "a" * 64,
        "trace_hash": "b" * 64,
        "oracle_hash": "c" * 64,
        "policy_hash": "d" * 64,
        "threshold_policy_hash": "e" * 64,
        "evidence_refs": (),
        "independently_recomputed": True,
        "producer_family": "deterministic",
        "grader_family": "deterministic",
        "context_relationship": "independent",
        "limitations": (),
        "redactions": (),
        "duration_ms": 1,
        "cost_microunits": 0,
        "executed_by_actor_id": f"act_{UUID7}",
    }
    with pytest.raises(ValueError, match="invalid verdict"):
        GraderResult(**(values | {"verdict": "maybe"}))
    with pytest.raises(ValueError, match="invalid grader_class"):
        GraderResult(**(values | {"grader_class": "X"}))


def test_evaluation_retry_gets_new_identity_and_clears_terminal_evidence():
    run = _run(
        state="failed",
        trace_ids=(f"trc_{UUID7}",),
        grader_result_ids=(f"grr_{UUID7}",),
        terminal_summary="infrastructure failure",
    )
    retry = run.retry("run_01978abc-0002-7000-8000-000000000002")
    assert retry.evaluation_run_id != run.evaluation_run_id
    assert retry.attempt_number == 2
    assert retry.retry_of == run.evaluation_run_id
    assert retry.state == "declared"
    assert retry.trace_ids == ()
    assert retry.grader_result_ids == ()
    assert retry.terminal_summary is None


def test_coverage_and_release_models_use_closed_stage_and_decision_enums():
    coverage = CoverageManifest(
        coverage_manifest_id=f"cvm_{UUID7}",
        changed_component="research_system.evals",
        baseline_version="main",
        candidate_version="wp4",
        affected_capabilities=("evaluation",),
        risk_tiers=("R2",),
        assurance_lanes=("provenance",),
        provider_variants=("none",),
        runtime_variants=("python-3.13-windows",),
        gate_stage="p0_materialization",
        selected_fixture_revisions=(("F-001", "r1"),),
        omitted_fixtures=(),
        required_result_keys=(("F-001", "r1", "state", "D", "v1"),),
        required_parity_controls=(),
        required_operations_scenarios=(),
        expected_evidence_classes=("command_receipt",),
        release_gate_policy_version="p0-release-v1",
    )
    assert coverage.gate_stage == "p0_materialization"
    with pytest.raises(ValueError, match="invalid decision"):
        ReleaseGateDecision(
            release_gate_decision_id=f"rgd_{UUID7}",
            coverage_manifest_id=coverage.coverage_manifest_id,
            baseline_identity="main",
            candidate_identity="wp4",
            evidence_snapshot_hash="f" * 64,
            required_verdicts=(),
            critical_failures=(),
            parity_status="pass",
            operations_status="pass",
            decision="accepted",
            decided_at="2026-07-03T12:00:00Z",
            canonical_event_ref=f"evt_{UUID7}",
        )


def test_exception_limited_requires_an_accepted_policy_binding():
    bounded_exception = {
        "decision": "exception_limited",
        "exception_scope": "provider-parity-only",
        "exception_expiry": "2026-07-10T12:00:00Z",
        "disabled_or_constrained_capability": "provider_execution",
        "human_authority_id": f"act_{UUID7}",
    }
    with pytest.raises(ValueError, match="accepted exception policy"):
        _release_decision(**bounded_exception)

    decision = _release_decision(
        **bounded_exception,
        exception_policy_id="p0-exception-policy-v1",
        exception_policy_hash="a" * 64,
    )
    assert decision.decision == "exception_limited"


def test_non_exception_decision_rejects_exception_fields():
    with pytest.raises(ValueError, match="require exception_limited"):
        _release_decision(
            exception_policy_id="p0-exception-policy-v1",
            exception_policy_hash="a" * 64,
        )


def test_release_schema_rejects_null_exception_policy_bindings():
    registry = SchemaRegistry(SCHEMAS)
    payload = {
        "schema_id": "ars://evals/release-gate-decision",
        "schema_version": "1.0.0",
        "release_gate_decision_id": f"rgd_{UUID7}",
        "coverage_manifest_id": f"cvm_{UUID7}",
        "baseline_identity": "main",
        "candidate_identity": "wp4",
        "evidence_snapshot_hash": "f" * 64,
        "required_verdicts": [],
        "critical_failures": [],
        "parity_status": "pass",
        "operations_status": "pass",
        "decision": "exception_limited",
        "decided_at": "2026-07-03T12:00:00Z",
        "canonical_event_ref": f"evt_{UUID7}",
        "exception_policy_id": None,
        "exception_policy_hash": None,
        "exception_scope": "provider-parity-only",
        "exception_expiry": "2026-07-10T12:00:00Z",
        "disabled_or_constrained_capability": "provider_execution",
        "human_authority_id": f"act_{UUID7}",
    }
    with pytest.raises(SchemaError, match="exception_policy"):
        registry.validate("ars://evals/release-gate-decision", payload)

    payload["exception_policy_id"] = "p0-exception-policy-v1"
    payload["exception_policy_hash"] = "a" * 64
    registry.validate("ars://evals/release-gate-decision", payload)


def test_eval_schemas_are_closed_and_reject_retired_gate_alias():
    registry = SchemaRegistry(SCHEMAS)
    payload = {
        "schema_id": "ars://evals/fixture-definition",
        "schema_version": "1.0.0",
        "fixture_id": "F-001",
        "fixture_revision": "r1",
        "title": "Single-slot overwrite",
        "owner": "evaluation_owner",
        "status": "authored",
        "incident_basis": "historical",
        "input_fidelity": "reconstructed",
        "risk_tier": "R2",
        "assurance_lanes": ["provenance"],
        "failure_class": "authority_overwrite",
        "priority": "P0",
        "gate_stage": "p0_materialization",
        "source_manifest_hash": "a" * 64,
        "decision_refs": ["P-030"],
        "policy_versions": ["canonical-policy-v1"],
        "schema_versions": ["fixture-definition-v1"],
        "confidentiality": "internal",
        "permitted_consumers": ["eval"],
        "setup_hash": "b" * 64,
        "stimulus_hash": "c" * 64,
        "pre_control_oracle_hash": "d" * 64,
        "post_control_oracle_hash": "e" * 64,
        "required_trajectory": ["two_messages_survive"],
        "forbidden_trajectory": ["overwrite"],
        "allowed_terminal_states": ["decided"],
        "expected_stop_semantics": "none",
        "required_graders": [
            {
                "grader_id": "state",
                "grader_class": "D",
                "grader_version": "v1",
                "critical": True,
                "required": True,
                "independence_requirement": "deterministic_independent",
                "evidence_selectors": ["command_receipt"],
            }
        ],
        "threshold_policy_ids": ["tp-1"],
        "required_evidence_classes": ["command_receipt"],
        "known_bad_reference_hash": "f" * 64,
        "known_good_reference_hash": "0" * 64,
        "mutation_ids": ["overwrite"],
        "safe_variation_ids": ["message_order"],
        "calibration_record_id": None,
        "retention_class": "R0",
        "retention_rule_id": "retain-with-decision",
        "redaction_policy_id": "redaction-v1",
    }
    registry.validate("ars://evals/fixture-definition", payload)
    payload["required_graders"][0]["evidence_selectors"] = []
    with pytest.raises(SchemaError, match="evidence_selectors"):
        registry.validate("ars://evals/fixture-definition", payload)
    payload["required_graders"][0]["evidence_selectors"] = ["command_receipt"]

    payload["gate_stage"] = "gate3_spec_review"
    with pytest.raises(SchemaError, match="gate_stage"):
        registry.validate("ars://evals/fixture-definition", payload)
    payload["gate_stage"] = "p0_materialization"
    payload["grader_results"] = []
    with pytest.raises(SchemaError, match="grader_results"):
        registry.validate("ars://evals/fixture-definition", payload)


def _valid_grader_result(**changes: object) -> GraderResult:
    values = {
        "grader_result_id": f"grr_{UUID7}",
        "evaluation_run_id": f"run_{UUID7}",
        "fixture_id": "F-001",
        "fixture_revision": "r1",
        "grader_id": "state",
        "grader_class": "D",
        "grader_version": "v1",
        "verdict": "pass",
        "severity": "critical",
        "critical": True,
        "required": True,
        "subject_hash": "a" * 64,
        "trace_hash": "b" * 64,
        "oracle_hash": "c" * 64,
        "policy_hash": "d" * 64,
        "threshold_policy_hash": "e" * 64,
        "evidence_refs": (),
        "independently_recomputed": True,
        "producer_family": "deterministic",
        "grader_family": "deterministic",
        "context_relationship": "deterministic_independent",
        "limitations": (),
        "redactions": (),
        "duration_ms": 1,
        "cost_microunits": 0,
        "executed_by_actor_id": f"act_{UUID7}",
    }
    values.update(changes)
    return GraderResult(**values)


@pytest.mark.parametrize("field", ["subject_hash", "policy_bundle_hash"])
def test_evaluation_run_rejects_invalid_hashes(field):
    with pytest.raises(ValueError, match=field):
        _run(**{field: "not-a-sha256"})


@pytest.mark.parametrize("field", ["start_sequence_position", "end_sequence_position"])
def test_evaluation_run_rejects_negative_sequence_positions(field):
    with pytest.raises(ValueError, match=field):
        _run(**{field: -1})


@pytest.mark.parametrize(
    "field",
    [
        "trace_ids",
        "provider_receipt_ids",
        "operational_record_ids",
        "grader_result_ids",
        "exception_refs",
        "quarantine_refs",
    ],
)
def test_evaluation_run_rejects_duplicate_evidence_references(field):
    with pytest.raises(ValueError, match=field):
        _run(**{field: ("duplicate", "duplicate")})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("severity", "fatal"),
        ("subject_hash", "not-a-sha256"),
        ("trace_hash", "not-a-sha256"),
        ("oracle_hash", "not-a-sha256"),
        ("policy_hash", "not-a-sha256"),
        ("threshold_policy_hash", "not-a-sha256"),
        ("evidence_refs", ("duplicate", "duplicate")),
        ("limitations", ("duplicate", "duplicate")),
        ("redactions", ("duplicate", "duplicate")),
        ("duration_ms", -1),
        ("cost_microunits", -1),
        ("supersedes", "invalid-id"),
    ],
)
def test_grader_result_rejects_schema_invalid_values(field, value):
    with pytest.raises(ValueError, match=field):
        _valid_grader_result(**{field: value})


def _eval_schema(name: str) -> dict[str, object]:
    path = SCHEMAS / "evals" / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_release_decision_schema_uses_exact_result_keys():
    schema = _eval_schema("release-gate-decision")
    for field in ("required_verdicts", "critical_failures"):
        item_schema = schema["$defs"]["resultKey"]
        assert item_schema["minItems"] == 5
        assert item_schema["maxItems"] == 5
        assert item_schema["prefixItems"][3]["enum"] == ["D", "T", "R", "M", "H", "O", "P"]


def test_trace_schema_requires_constructor_routing_fields():
    schema = _eval_schema("trace-envelope")
    required = set(schema["required"])
    assert {
        "route_decision_id",
        "routing_evidence_snapshot_id",
        "canonical_policy_bundle_id",
        "adapter_manifest_version",
    } <= required


def test_fixture_schema_closes_independence_vocabulary():
    schema = _eval_schema("fixture-definition")
    independence = schema["$defs"]["graderRequirement"]["properties"]["independence_requirement"]
    assert independence == {
        "enum": [
            "deterministic_independent",
            "cross_family_context_independent",
        ]
    }
