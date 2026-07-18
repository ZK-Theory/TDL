"""Unit-level guards for the re-scoped T1.38 production runner."""

import re
from pathlib import Path
from types import SimpleNamespace

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
    assert model["projected_units"] == len(runner.DATASETS) * len(runner.VALID_NULLS) * 2 * 2
    assert model["ram_preflight_passed"] is False


def test_runner_requires_preflight_selected_worker_count_and_budget() -> None:
    args = runner.parse_args(["--only", "usoc:order_shuffle", "--worker-count", "3", "--wall-time-hours", "6"])
    assert args.worker_count == 3
    assert args.wall_time_hours == 6
    with pytest.raises(SystemExit):
        runner.parse_args(["--only", "usoc:order_shuffle"])
    assert runner._preflight_classification({"projected_wall_hours": 6.1, "ram_preflight_passed": True}, 6) == "STOP"


@pytest.mark.integration
def test_project_root_is_resolved_from_git_common_dir() -> None:
    assert runner.PROJ_ROOT == audit_lib.project_root(runner.WORKTREE_ROOT)


@pytest.mark.integration
def test_git_metadata_reads_worktree_files() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", audit_lib.git_head(runner.WORKTREE_ROOT))


def test_git_metadata_reads_linked_worktree_files(tmp_path: Path) -> None:
    common_dir = tmp_path / ".git"
    git_dir = common_dir / "worktrees" / "audit"
    worktree = tmp_path / "linked-worktree"
    git_dir.mkdir(parents=True)
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {git_dir}\n", encoding="utf-8")
    (git_dir / "commondir").write_text("../..\n", encoding="utf-8")
    (git_dir / "HEAD").write_text("ref: refs/heads/audit\n", encoding="utf-8")
    ref = common_dir / "refs" / "heads" / "audit"
    ref.parent.mkdir(parents=True)
    ref.write_text(f"{'a' * 40}\n", encoding="utf-8")

    assert audit_lib.project_root(worktree) == tmp_path
    assert audit_lib.git_head(worktree) == "a" * 40


def test_main_passes_requested_permutation_count_to_assemble(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_assemble(date: str, worker_count: int, n_permutations: int) -> Path:
        captured.update(date=date, worker_count=worker_count, n_permutations=n_permutations)
        return Path("assembled.json")

    monkeypatch.setattr(
        runner,
        "parse_args",
        lambda: SimpleNamespace(assemble=True, date="2026-07-16", worker_count=3, n_permutations=7),
    )
    monkeypatch.setattr(runner, "assemble", fake_assemble)
    runner.main()
    assert captured == {"date": "2026-07-16", "worker_count": 3, "n_permutations": 7}


def test_exact_w2_pvalue_records_its_rank_count() -> None:
    stats = audit_lib.headline_stats_from_distances(np.asarray([4.0, 5.0]), np.asarray([1.0, 3.0, 6.0]))
    assert stats["rank_count_upper"] == 1
    assert stats["w2_pvalue"] == pytest.approx((1 + 1) / (3 + 1))
