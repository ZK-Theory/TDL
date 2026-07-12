import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from research_system.adapters.base import TransportResult
from research_system.adapters.fake import FakeTransport
from research_system.evals.errors import FixtureDefinitionError
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
    assert len(evidence.results) == 302
    assert len({item.result_key for item in evidence.results}) == 302
    assert decide_p0_release(evidence)["decision"] == "blocked"


def test_changed_second_fake_observation_is_rejected_before_evidence():
    with pytest.raises(ValueError, match="second-run"):
        build_observed_assertion_evidence(
            "adapter_policy_parity",
            {"semantic_parity": True},
            {"semantic_parity": False},
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
    assert len(transports) == 92
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
    evidence = replace(gate5_evidence, policy_applicability=conflicting)
    decision, _ = build_release_decision(
        evidence,
        run_all_scenarios(),
        decided_at="2026-07-13T00:00:00Z",
    )
    assert decision.parity_status == "blocked"
    assert decision.decision == "blocked"


def test_evaluation_evidence_rejects_untyped_parity_artifacts(gate5_evidence):
    with pytest.raises(TypeError, match="PolicyParityReport"):
        replace(gate5_evidence, parity_report=object())
