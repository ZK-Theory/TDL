import shutil
from dataclasses import asdict, fields, replace
from pathlib import Path

import pytest

from research_system.adapters.base import TransportResult
from research_system.adapters.fake import FakeTransport
from research_system.canonical import jsonable
from research_system.evals.errors import FixtureDefinitionError
from research_system.evals import variants
from research_system.evals.harness import (
    build_release_decision,
    decide_p0_release,
    run_all_scenarios,
    run_p0_coverage,
)
from research_system.evals.variants import (
    build_observed_assertion_evidence,
    execute_gate5_variant_rows_twice,
    load_gate5_variant_rows,
)
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"


@pytest.fixture(scope="module")
def gate5_evidence():
    return run_p0_coverage(
        EVALS / "p0-coverage.yaml",
        fixture_root=EVALS / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
    )


def test_gate5_rows_execute_twice_fake_only_and_close_302_keys(gate5_evidence):
    evidence = gate5_evidence
    assert len(evidence.variant_executions) == 46
    assert all(item.decisions_equal for item in evidence.variant_executions)
    assert all(
        item.first_normalized_decision_hash == item.second_normalized_decision_hash
        for item in evidence.variant_executions
    )
    assert all(item.oracle_match for item in evidence.variant_executions)
    assert all(
        item.expected_evidence_hash == item.first_observed_evidence_hash == item.second_observed_evidence_hash
        for item in evidence.variant_executions
    )
    assert len(evidence.results) == 302
    assert len({item.result_key for item in evidence.results}) == 302
    assert decide_p0_release(evidence)["decision"] == "blocked"
    payload = jsonable(asdict(evidence.variant_executions[0]))
    payload.update(
        schema_id="ars://evals/variant-execution-evidence",
        schema_version="1.0.0",
    )
    SchemaRegistry(ROOT / ".research-system" / "schemas").validate(
        "ars://evals/variant-execution-evidence",
        payload,
    )


def test_changed_second_fake_observation_is_rejected_before_evidence():
    with pytest.raises(ValueError, match="second-run"):
        build_observed_assertion_evidence(
            "adapter_policy_parity",
            {"semantic_parity": True},
            {"semantic_parity": False},
        )


def test_wrong_f007_producer_observation_cannot_inherit_passing_variant_verdicts(monkeypatch):
    """A stable non-parity producer error blocks its own variant graders."""
    original = variants.require_executor

    def wrong_f007_executor(fixture_id):
        execute = original(fixture_id)
        if fixture_id != "F-007":
            return execute

        def execute_wrong(subject, payload):
            observed = execute(subject, payload)
            return {**observed, "producer_seam_corruption": True}

        return replace(execute, execute_raw=execute_wrong)

    monkeypatch.setattr(variants, "require_executor", wrong_f007_executor)
    evidence = run_p0_coverage(
        EVALS / "p0-coverage.yaml",
        fixture_root=EVALS / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
    )
    f007_variants = tuple(
        item for item in evidence.results if item.fixture_id == "F-007" and item.variant_id != "baseline"
    )
    assert len(f007_variants) == 8
    assert {item.verdict for item in f007_variants} == {"fixture_error"}
    assert evidence.parity_report.passed is True
    assert decide_p0_release(evidence)["decision"] == "blocked"
    assert evidence.coverage.gate5_authorized is False


def test_all_registered_matrix_executor_provider_families_fail_closed_on_wrong_observations(
    gate5_evidence, monkeypatch
):
    """Exercise every committed executor/row family without copied test cases."""
    original = variants.require_executor
    observed_families = set()

    def wrong_executor(fixture_id):
        execute = original(fixture_id)

        def execute_wrong(subject, payload):
            observed_families.add((fixture_id, payload["_provider_variant"]))
            return {
                **execute.execute_raw(subject, payload),
                "producer_seam_corruption": fixture_id,
            }

        return replace(execute, execute_raw=execute_wrong)

    monkeypatch.setattr(variants, "require_executor", wrong_executor)
    rows = load_gate5_variant_rows(EVALS / "p0-variant-matrix.yaml", gate5_evidence.coverage)
    executions, results = execute_gate5_variant_rows_twice(
        rows,
        gate5_evidence.coverage,
        fixture_root=EVALS / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
        baseline_results=tuple(item for item in gate5_evidence.results if item.variant_id == "baseline"),
        fake_transport_factory=FakeTransport,
    )
    expected_families = {(row.fixture_id, row.provider_variant) for row in rows}
    assert observed_families == expected_families
    assert {row.provider_variant.split("-")[1] for row in rows} == {"claude", "codex"}
    assert {row.provider_variant.endswith("-count-v1") for row in rows} == {False, True}
    assert all(not execution.oracle_match for execution in executions)
    assert {item.verdict for item in results} == {"fixture_error"}


def test_variant_repeat_mismatch_stops_before_evidence_admission(gate5_evidence, monkeypatch):
    original = variants.require_executor
    calls = 0

    def alternating_f007_executor(fixture_id):
        execute = original(fixture_id)
        if fixture_id != "F-007":
            return execute

        def execute_alternating(subject, payload):
            nonlocal calls
            calls += 1
            observed = execute(subject, payload)
            return observed if calls == 1 else {**observed, "second_run_only": True}

        return replace(execute, execute_raw=execute_alternating)

    monkeypatch.setattr(variants, "require_executor", alternating_f007_executor)
    rows = load_gate5_variant_rows(EVALS / "p0-variant-matrix.yaml", gate5_evidence.coverage)
    with pytest.raises(ValueError, match="variant repeat mismatch"):
        execute_gate5_variant_rows_twice(
            rows,
            gate5_evidence.coverage,
            fixture_root=EVALS / "fixtures",
            schema_root=ROOT / ".research-system" / "schemas",
            baseline_results=tuple(item for item in gate5_evidence.results if item.variant_id == "baseline"),
            fake_transport_factory=FakeTransport,
        )


def test_gate5_rows_execute_through_both_provider_specific_fake_transports(gate5_evidence):
    transports = []

    def factory(results: list[TransportResult]) -> FakeTransport:
        transport = FakeTransport(results)
        transports.append(transport)
        return transport

    rows = load_gate5_variant_rows(EVALS / "p0-variant-matrix.yaml", gate5_evidence.coverage)
    baseline = tuple(item for item in gate5_evidence.results if item.variant_id == "baseline")
    execute_gate5_variant_rows_twice(
        rows,
        gate5_evidence.coverage,
        fixture_root=EVALS / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
        baseline_results=baseline,
        fake_transport_factory=factory,
    )
    assert len(transports) == 60
    argv = {invocation[0][0] for transport in transports for invocation in transport.invocations}
    assert argv == {"claude", "codex"}


def test_gate5_execution_rejects_tampered_materialized_package(gate5_evidence, tmp_path):
    fixture_root = tmp_path / "fixtures"
    shutil.copytree(EVALS / "fixtures", fixture_root)
    stimulus_path = fixture_root / "F-020" / "input" / "stimulus.json"
    stimulus = stimulus_path.read_text(encoding="utf-8").replace("compare_adapter_policies", "tampered")
    stimulus_path.write_text(stimulus, encoding="utf-8")
    rows = load_gate5_variant_rows(EVALS / "p0-variant-matrix.yaml", gate5_evidence.coverage)
    baseline = tuple(item for item in gate5_evidence.results if item.variant_id == "baseline")
    with pytest.raises(FixtureDefinitionError, match="content hash mismatch"):
        execute_gate5_variant_rows_twice(
            rows,
            gate5_evidence.coverage,
            fixture_root=fixture_root,
            schema_root=ROOT / ".research-system" / "schemas",
            baseline_results=baseline,
            fake_transport_factory=FakeTransport,
        )


def test_conflicting_applicability_binding_blocks_release(gate5_evidence):
    conflicting = replace(gate5_evidence.policy_applicability, applicability_hash="0" * 64)
    with pytest.raises(ValueError, match="accepted D-G5-5"):
        replace(gate5_evidence, policy_applicability=conflicting)


def test_evaluation_evidence_rejects_untyped_parity_artifacts(gate5_evidence):
    with pytest.raises(TypeError, match="PolicyParityReport"):
        replace(gate5_evidence, parity_report=object())


def test_direct_typed_parity_self_attestation_cannot_reach_release_pass(gate5_evidence):
    with pytest.raises(ValueError, match="parity report identity"):
        replace(
            gate5_evidence.parity_report,
            policy_parity_report_id="ppr_" + "0" * 64,
            report_hash="0" * 64,
            passed=True,
            blocking_controls=(),
        )


def test_release_rebuild_blocks_typed_report_that_bypasses_constructor_validation(gate5_evidence):
    forged_report = object.__new__(type(gate5_evidence.parity_report))
    for field in fields(gate5_evidence.parity_report):
        object.__setattr__(
            forged_report,
            field.name,
            getattr(gate5_evidence.parity_report, field.name),
        )
    object.__setattr__(forged_report, "report_hash", "0" * 64)
    object.__setattr__(forged_report, "policy_parity_report_id", "ppr_" + "0" * 64)

    forged_evidence = object.__new__(type(gate5_evidence))
    for field in fields(gate5_evidence):
        object.__setattr__(
            forged_evidence,
            field.name,
            forged_report if field.name == "parity_report" else getattr(gate5_evidence, field.name),
        )
    decision, _ = build_release_decision(
        forged_evidence,
        run_all_scenarios(),
        decided_at="2026-07-13T00:00:00Z",
    )
    assert decision.parity_status == "blocked"
    assert decision.decision == "blocked"
