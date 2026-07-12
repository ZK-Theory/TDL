from pathlib import Path

from research_system.evals.harness import decide_p0_release, run_p0_coverage
from research_system.evals.variants import build_observed_assertion_evidence
import pytest


ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"


def test_gate5_rows_execute_twice_fake_only_and_close_302_keys():
    evidence = run_p0_coverage(
        EVALS / "p0-coverage.yaml",
        fixture_root=EVALS / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
    )
    assert len(evidence.variant_executions) == 46
    assert all(item.decisions_equal for item in evidence.variant_executions)
    assert all(item.first_normalized_decision_hash == item.second_normalized_decision_hash for item in evidence.variant_executions)
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
