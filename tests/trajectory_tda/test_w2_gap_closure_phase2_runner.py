"""Unit-level guards for the re-scoped T1.38 production runner."""

from scratch.w2_fallback_audit import w2_gap_closure_table1_h1 as runner


def test_phase2_runner_excludes_set_invariant_pseudonulls() -> None:
    assert set(runner.VALID_NULLS) == {"order_shuffle", "markov1", "markov2", "stratified_markov1"}
    invalid = runner.invalid_null_classifications()
    assert set(invalid) == {"label_shuffle", "cohort_shuffle"}
    assert all(row["classification"] == "INVALID-BY-CONSTRUCTION" for row in invalid.values())
    assert all("set-valued" in row["reason"] for row in invalid.values())


def test_parallel_cost_model_requires_ram_headroom() -> None:
    summary = {
        "cost": {
            "generation_plus_obs_w2_seconds": [60.0, 70.0],
            "null_null_w2_seconds_per_unit": 10.0,
            "per_process_peak_gb": 8.0,
            "free_gb_at_launch": 20.0,
        }
    }
    model = runner._cost_model([summary], n_permutations=2, worker_count=2)
    assert model["worker_count"] == 2
    assert model["projected_wall_hours"] > 0
    assert model["ram_preflight_passed"] is False
