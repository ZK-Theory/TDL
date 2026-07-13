from pathlib import Path
from dataclasses import asdict
from dataclasses import replace

import pytest

from research_system.adapters.parity import build_parity_report
from research_system.adapters.parity_evidence import build_fake_adapter_parity_evidence
from research_system.canonical import canonical_bytes, jsonable, sha256_hex
from research_system.errors import SchemaError
from research_system.evals.harness import run_p0_coverage
from research_system.evals.variants import load_gate5_variant_rows
from research_system.policy.loader import load_canonical_policy_bundle, load_policy_control_applicability
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"
POLICIES = ROOT / ".research-system" / "policies"


@pytest.fixture(scope="module")
def execution():
    return run_p0_coverage(
        EVALS / "p0-coverage.yaml",
        fixture_root=EVALS / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
    )


def test_real_typed_fake_evidence_closes_every_control_provider_pair(execution):
    assert execution.parity_report.passed is True
    assert execution.parity_report.blocking_controls == ()
    assert len(execution.parity_report.rows) == 4
    assert len(execution.parity_evidence) == 8
    registry = SchemaRegistry(ROOT / ".research-system" / "schemas")
    for record in execution.parity_evidence:
        evidence_payload = jsonable(asdict(record))
        evidence_payload.update(
            schema_id="ars://adapters/fake-adapter-parity-evidence",
            schema_version="1.0.0",
        )
        registry.validate("ars://adapters/fake-adapter-parity-evidence", evidence_payload)
    payload = jsonable(asdict(execution.parity_report))
    payload.update(schema_id="ars://adapters/parity-report", schema_version="1.0.0")
    registry.validate("ars://adapters/parity-report", payload)
    del payload["rows"][0]["control_revision"]
    with pytest.raises(SchemaError, match="control_revision"):
        registry.validate("ars://adapters/parity-report", payload)


def test_plain_or_self_attested_manifest_is_rejected(execution):
    bundle = load_canonical_policy_bundle(POLICIES / "canonical-policy.yaml")
    applicability = load_policy_control_applicability(
        POLICIES / "gate5-policy-control-applicability.yaml", bundle=bundle
    )
    with pytest.raises(TypeError, match="typed"):
        build_parity_report(
            bundle,
            applicability,
            ({"passed": True},),
            executions=execution.variant_executions,
            matrix_rows=execution.variant_rows,
            results=execution.results,
        )
    with pytest.raises(TypeError, match="typed"):
        build_fake_adapter_parity_evidence(
            ({"disposition": "adapter_enforced"},),
            applicability,
            bundle,
            matrix_rows=(),
            results=(),
        )


def test_empty_applicability_cannot_produce_a_parity_percentage(execution):
    bundle = load_canonical_policy_bundle(POLICIES / "canonical-policy.yaml")
    applicability = load_policy_control_applicability(
        POLICIES / "gate5-policy-control-applicability.yaml",
        bundle=bundle,
    )
    with pytest.raises(ValueError, match="at least one control"):
        build_parity_report(
            bundle,
            replace(applicability, controls=()),
            (),
            executions=execution.variant_executions,
            matrix_rows=execution.variant_rows,
            results=execution.results,
        )


def test_missing_or_diagnostic_critical_evidence_cannot_be_averaged_to_pass(execution):
    bundle = load_canonical_policy_bundle(POLICIES / "canonical-policy.yaml")
    missing = build_parity_report(
        bundle,
        execution.policy_applicability,
        execution.parity_evidence[:-1],
        executions=execution.variant_executions,
        matrix_rows=execution.variant_rows,
        results=execution.results,
    )
    assert missing.passed is False
    assert missing.diagnostic_percentage >= 75
    with pytest.raises(ValueError, match="disposition"):
        replace(execution.parity_evidence[-1], disposition="diagnostic_only")


def test_parity_producer_requires_exact_matrix_and_release_result_closure(execution):
    bundle = load_canonical_policy_bundle(POLICIES / "canonical-policy.yaml")
    f020_only = tuple(item for item in execution.variant_executions if item.matrix_row.fixture_id == "F-020")
    rows = load_gate5_variant_rows(EVALS / "p0-variant-matrix.yaml", execution.coverage)
    with pytest.raises(ValueError, match="46-row"):
        build_fake_adapter_parity_evidence(
            f020_only,
            execution.policy_applicability,
            bundle,
            matrix_rows=rows,
            results=execution.results,
        )


def test_forged_typed_evidence_identity_cannot_produce_a_passing_report(execution):
    with pytest.raises(ValueError, match="evidence identity"):
        replace(
            execution.parity_evidence[0],
            evidence_id="fpe_" + "0" * 64,
            evidence_hash="0" * 64,
        )


def test_valid_typed_evidence_rejects_variant_id_drift(execution):
    valid = execution.parity_evidence[0]
    with pytest.raises(ValueError, match="evidence identity"):
        replace(valid, variant_id="variant-forged")


def _replace_execution_bindings(execution, donor):
    payload = {
        "matrix_tuple": list(execution.matrix_row.matrix_tuple),
        "first_hash": execution.first_normalized_decision_hash,
        "second_hash": execution.second_normalized_decision_hash,
        "grader_result_keys": [list(item) for item in donor.grader_result_keys],
        "grader_results": [
            [list(item[0]), *item[1:]] for item in donor.grader_result_bindings
        ],
        "observed_assertions": [
            {
                "property": item.property,
                "json_pointer": item.json_pointer,
                "canonical_observed_value": item.canonical_observed_value,
                "first_observed_value_hash": item.first_observed_value_hash,
                "second_observed_value_hash": item.second_observed_value_hash,
                "equal": item.equal,
            }
            for item in execution.observed_assertions
        ],
    }
    return replace(
        execution,
        grader_result_keys=donor.grader_result_keys,
        grader_result_bindings=donor.grader_result_bindings,
        execution_evidence_hash=sha256_hex(canonical_bytes(payload)),
    )


def test_parity_producer_rejects_typed_execution_with_other_rows_result_bindings(execution):
    bundle = load_canonical_policy_bundle(POLICIES / "canonical-policy.yaml")
    rows = load_gate5_variant_rows(EVALS / "p0-variant-matrix.yaml", execution.coverage)
    target = execution.variant_executions[0]
    donor = next(
        item
        for item in execution.variant_executions[1:]
        if len(item.grader_result_keys) == len(target.grader_result_keys)
    )
    forged = _replace_execution_bindings(target, donor)
    executions = (forged, *execution.variant_executions[1:])
    with pytest.raises(ValueError, match="grader result binding"):
        build_fake_adapter_parity_evidence(
            executions,
            execution.policy_applicability,
            bundle,
            matrix_rows=rows,
            results=execution.results,
        )


def test_parity_producer_rejects_unrelated_release_result(execution):
    bundle = load_canonical_policy_bundle(POLICIES / "canonical-policy.yaml")
    rows = load_gate5_variant_rows(EVALS / "p0-variant-matrix.yaml", execution.coverage)
    results = list(execution.results)
    index = next(i for i, item in enumerate(results) if item.variant_id != "baseline")
    results[index] = replace(results[index], variant_id="unrelated-variant")
    with pytest.raises(ValueError, match="unrelated variant release result"):
        build_fake_adapter_parity_evidence(
            execution.variant_executions,
            execution.policy_applicability,
            bundle,
            matrix_rows=rows,
            results=tuple(results),
        )
