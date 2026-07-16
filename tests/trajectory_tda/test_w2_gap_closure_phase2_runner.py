"""Unit-level guards for the re-scoped T1.38 production runner."""

from scratch.w2_fallback_audit import w2_gap_closure_table1_h1 as runner


def test_phase2_runner_excludes_set_invariant_pseudonulls() -> None:
    assert set(runner.VALID_NULLS) == {"order_shuffle", "markov1", "markov2", "stratified_markov1"}
    invalid = runner.invalid_null_classifications()
    assert set(invalid) == {"label_shuffle", "cohort_shuffle"}
    assert all(row["classification"] == "INVALID-BY-CONSTRUCTION" for row in invalid.values())
    assert all("set-valued" in row["reason"] for row in invalid.values())
