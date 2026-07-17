"""Unit-level guards for the re-scoped T1.38 production runner."""

import re

import numpy as np
import pytest

from scratch.w2_fallback_audit import w2_gap_closure_table1_h1 as runner
from scratch.w2_fallback_audit import audit_lib


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


def test_runner_requires_preflight_selected_worker_count_and_budget() -> None:
    args = runner.parse_args(["--only", "usoc:order_shuffle", "--worker-count", "3", "--wall-time-hours", "6"])
    assert args.worker_count == 3
    assert args.wall_time_hours == 6
    with pytest.raises(SystemExit):
        runner.parse_args(["--only", "usoc:order_shuffle"])
    assert runner._preflight_classification({"projected_wall_hours": 6.1, "ram_preflight_passed": True}, 6) == "STOP"


def test_project_root_is_resolved_from_git_common_dir() -> None:
    assert runner.PROJ_ROOT == audit_lib.project_root(runner.WORKTREE_ROOT)


def test_git_metadata_uses_a_resolved_executable() -> None:
    assert audit_lib.git_executable_path().is_absolute()
    assert re.fullmatch(r"[0-9a-f]{40}", audit_lib.git_head(runner.WORKTREE_ROOT))


def test_exact_w2_pvalue_records_its_rank_count() -> None:
    stats = audit_lib.headline_stats_from_distances(np.asarray([4.0, 5.0]), np.asarray([1.0, 3.0, 6.0]))
    assert stats["rank_count_upper"] == 1
    assert stats["w2_pvalue"] == pytest.approx((1 + 1) / (3 + 1))
