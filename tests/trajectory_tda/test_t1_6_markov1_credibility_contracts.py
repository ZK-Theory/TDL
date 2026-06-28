# Research context: contracts/stage1-output-schemas
# Purpose: Binding tests for T1.6 BHPS Markov-1 credibility diagnostics.
"""Contract bindings for BHPS Markov-1 credibility outputs."""

from __future__ import annotations

import copy
import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
OUTPUT_GLOB = "results/trajectory_tda_bhps/diagnostics/markov1_calibration_*.json"
MODULE_NAME = "trajectory_tda.scripts.stage1.run_bhps_markov1_credibility"


def _load_contract(rel_path: str) -> dict[str, Any]:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _matched_jsons(glob_pattern: str) -> list[Path]:
    matched: list[Path] = []
    for path in REPO_ROOT.rglob("*.json"):
        rel = path.relative_to(REPO_ROOT)
        if rel.full_match(glob_pattern):
            matched.append(path)
    return matched


def _validator():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None, f"missing module {MODULE_NAME}"
    module = importlib.import_module(MODULE_NAME)
    return module.validate_bhps_markov1_credibility_payload


def _payload(
    *,
    ks_p: float = 0.25,
    calibrated: bool = True,
    bhps_cv: float = 0.7,
    usoc_cv: float = 1.0,
    variance_flag: bool = False,
    verdict: str = "credible",
) -> dict[str, Any]:
    return {
        "schema_version": "stage1/bhps-markov1-credibility/v1",
        "generated_at": "2026-06-20T00:00:00+00:00",
        "task": "T1.6 BHPS Markov-1 rejection credibility under valid frozen-loadings nulls",
        "pre_registration": (
            "2026-06-13 T1.6 amendment at " "results/trajectory_tda_bhps/diagnostics/pre_registrations_2026-06-13.json"
        ),
        "inputs": {
            "git_head": "d95ee9e",
            "bhps_null_cache": {
                "path": "results/trajectory_tda_integration/stage1/cache/"
                "null_diagrams_bhps_frozen_B1000_L5000_seed42_2026-05-28.npz",
                "metadata": {"B": 1000, "L": 5000, "seed": 42, "frozen_loadings": True},
            },
            "usoc_null_cache": {
                "path": "results/trajectory_tda_integration/stage1/cache/"
                "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz",
                "metadata": {"B": 1000, "L": 5000, "seed": 42, "frozen_loadings": True},
            },
        },
        "params": {
            "null_model": "markov-1",
            "frozen_loadings": True,
            "L": 5000,
            "seed": 42,
            "n_calibration_trials": 100,
            "calibration_null_bank_B": 200,
            "p_value_formula": "(r+1)/(B+1)",
        },
        "calibration": {
            "ks_statistic": 0.12,
            "ks_p": ks_p,
            "mean_pvalue": 0.48,
            "calibrated": calibrated,
        },
        "variance": {
            "bhps_nullnull_cv": bhps_cv,
            "usoc_nullnull_cv": usoc_cv,
            "variance_flag": variance_flag,
        },
        "decision": {"verdict": verdict},
    }


def _assert_no_errors(errors: list[str]) -> None:
    assert not errors, "; ".join(errors)


def test_bhps_markov1_credibility_output_schema() -> None:
    """Representative payload passes; contract-listed violations reject."""
    validate_payload = _validator()
    _assert_no_errors(validate_payload(_payload()))

    # (a) calibration.calibrated disagrees with (ks_p >= 0.05)
    bad = _payload(ks_p=0.25, calibrated=False)
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_payload(bad))

    # (b) variance.variance_flag disagrees with (bhps_nullnull_cv < 0.5 * usoc_nullnull_cv)
    bad = _payload(bhps_cv=0.2, usoc_cv=1.0, variance_flag=False)
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_payload(bad))

    # (c) decision.verdict disagrees with calibrated/variance_flag coupling
    bad = _payload(ks_p=0.01, calibrated=False, variance_flag=False, verdict="credible")
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_payload(bad))

    bad = _payload(bhps_cv=0.2, usoc_cv=1.0, variance_flag=True, verdict="credible")
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_payload(bad))

    bad = _payload(verdict="suspect")
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_payload(bad))

    # (d) p-values/statistics/CVs are outside allowed ranges
    bad = _payload()
    bad["calibration"]["ks_p"] = 1.1
    bad["calibration"]["mean_pvalue"] = -0.1
    bad["calibration"]["ks_statistic"] = -0.01
    bad["variance"]["bhps_nullnull_cv"] = 0.0
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_payload(bad))

    # (e) locked parameters disagree with the pre-registration
    bad = _payload()
    bad["params"].update(
        {
            "null_model": "markov",
            "frozen_loadings": False,
            "L": 2500,
            "seed": 7,
            "n_calibration_trials": 99,
            "calibration_null_bank_B": 99,
            "p_value_formula": "r/B",
        }
    )
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_payload(bad))

    # (f) the forbidden key per_call_pca is present
    bad = _payload()
    bad["per_call_pca"] = True
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_payload(bad))


def test_bhps_markov1_credibility_json_validation_dispatch() -> None:
    output_validation = _load_contract("stage1-output-schemas/bhps-markov1-credibility-output-json-validation.yaml")
    ov = output_validation["output_validation"]
    assert ov["applies_to_glob"] == OUTPUT_GLOB
    assert ov["schema_contracts"] == ["bhps-markov1-credibility-output"]
    assert Path("results/trajectory_tda_bhps/diagnostics/markov1_calibration_2026-06-20.json").full_match(
        ov["applies_to_glob"]
    )
    assert not Path("results/trajectory_tda_bhps/diagnostics/markov1_nullnull_variance_2026-06-20.json").full_match(
        ov["applies_to_glob"]
    )

    validate_payload = _validator()
    for json_path in _matched_jsons(ov["applies_to_glob"]):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        _assert_no_errors(validate_payload(payload))


def test_bhps_markov1_credibility_validator_is_pure() -> None:
    validate_payload = _validator()
    payload = _payload()
    before = copy.deepcopy(payload)
    validate_payload(payload)
    assert payload == before


def test_benchmark_only_limits_null_pair_work_and_checkpoints(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = importlib.import_module(MODULE_NAME)
    seen_pair_counts: list[int] = []

    class InlineParallel:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_distance_batch(parallel, pairs, diagrams, dim):
        seen_pair_counts.append(len(pairs))
        return [1.0] * len(pairs)

    def fake_obs_to_bank_distances(parallel, observed, bank, dim):
        return [1.0] * len(bank)

    monkeypatch.setattr(module, "Parallel", InlineParallel)
    monkeypatch.setattr(module, "_distance_batch", fake_distance_batch)
    monkeypatch.setattr(module, "_obs_to_bank_distances", fake_obs_to_bank_distances)

    cache = {"h0_diagrams": [np.array([[0.0, float(i + 1)]]) for i in range(20)]}
    checkpoint_path = tmp_path / "progress.json"
    result = module.compute_calibration(
        cache,
        n_trials=5,
        bank_b=10,
        seed=42,
        workers=4,
        backend="threading",
        checkpoint_path=checkpoint_path,
        benchmark_only=True,
        benchmark_trials=1,
        benchmark_null_pairs=2,
    )

    assert seen_pair_counts == [2]
    assert result["completed_trials"] == 1
    assert checkpoint_path.exists()
    assert result["full_design_distances_projected"] == 60
    assert "projected_calibration_full_design_s" in result
    # Benchmark saturates the timed trial batch to >= 2x workers (here 2*4=8) so
    # elapsed/count reflects steady-state throughput, not a sub-pool burst.
    assert result["benchmark_bank_B"] == 8
    assert result["benchmark_distances_timed"] > 4

    seen_pair_counts.clear()
    full_result = module.compute_calibration(
        cache,
        n_trials=5,
        bank_b=10,
        seed=42,
        workers=4,
        backend="threading",
        checkpoint_path=checkpoint_path,
        benchmark_only=False,
        benchmark_trials=1,
        benchmark_null_pairs=2,
    )

    assert seen_pair_counts == [10]
    assert full_result["calibration_null_bank_B"] == 10
    assert len(full_result["trial_details"]) == 5

    seed_checkpoint_path = tmp_path / "seed-progress.json"
    module.compute_calibration(
        cache,
        n_trials=5,
        bank_b=10,
        seed=42,
        workers=4,
        backend="threading",
        checkpoint_path=seed_checkpoint_path,
        benchmark_only=True,
        benchmark_trials=1,
        benchmark_null_pairs=2,
    )

    seen_pair_counts.clear()
    module.compute_calibration(
        cache,
        n_trials=5,
        bank_b=10,
        seed=43,
        workers=4,
        backend="threading",
        checkpoint_path=seed_checkpoint_path,
        benchmark_only=True,
        benchmark_trials=1,
        benchmark_null_pairs=2,
    )

    assert seen_pair_counts == [2]


def test_benchmark_requires_more_distances_than_workers(tmp_path: Path) -> None:
    """The benchmark must time more distances than workers, else elapsed/count
    understates the true per-distance cost (the attempt-#2 4.7x-optimistic bug)."""
    module = importlib.import_module(MODULE_NAME)
    cache = {"h0_diagrams": [np.array([[0.0, float(i + 1)]]) for i in range(20)]}
    # bank_b (4) cannot be saturated beyond a 10-worker pool -> guard must trip
    # before any real W2 work is dispatched.
    with pytest.raises(ValueError, match="more distances than workers"):
        module.compute_calibration(
            cache,
            n_trials=5,
            bank_b=4,
            seed=42,
            workers=10,
            backend="loky",
            checkpoint_path=tmp_path / "guard-progress.json",
            benchmark_only=True,
            benchmark_trials=1,
            benchmark_null_pairs=2,
        )


def test_serial_backend_computes_without_joblib(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """backend='serial' runs the distance loops in-process, never touching joblib."""
    module = importlib.import_module(MODULE_NAME)

    def fast_w2(a, b, dim):
        return float(abs(float(a[0][1]) - float(b[0][1])))

    def boom(*args, **kwargs):
        raise AssertionError("joblib Parallel must not be used in serial mode")

    monkeypatch.setattr(module, "_w2", fast_w2)
    monkeypatch.setattr(module, "Parallel", boom)

    cache = {"h0_diagrams": [np.array([[0.0, float(i + 1)]]) for i in range(40)]}
    result = module.compute_calibration(
        cache,
        n_trials=3,
        bank_b=5,
        seed=42,
        workers=6,
        backend="serial",
        checkpoint_path=tmp_path / "serial-progress.json",
        benchmark_only=False,
    )
    assert len(result["trial_details"]) == 3
    assert result["calibration_null_bank_B"] == 5
    # Per-trial obs-to-bank distance array is persisted for provenance/resume.
    assert all(len(row["obs_null_distances"]) == 5 for row in result["trial_details"])


def test_serial_per_trial_checkpoint_resume_skips_completed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A resumed serial run reuses the cached null bank and skips completed trials."""
    module = importlib.import_module(MODULE_NAME)
    cache = {"h0_diagrams": [np.array([[0.0, float(i + 1)]]) for i in range(40)]}
    checkpoint = tmp_path / "resume-progress.json"

    monkeypatch.setattr(module, "_w2", lambda a, b, dim: 1.0)
    first = module.compute_calibration(
        cache,
        n_trials=3,
        bank_b=5,
        seed=42,
        workers=6,
        backend="serial",
        checkpoint_path=checkpoint,
        benchmark_only=False,
    )
    assert len(first["trial_details"]) == 3

    # Re-run against the same checkpoint: every distance must already be cached, so
    # _w2 is never called again (null bank reused + all trials skipped).
    calls = {"n": 0}

    def counting_w2(a, b, dim):
        calls["n"] += 1
        return 1.0

    monkeypatch.setattr(module, "_w2", counting_w2)
    second = module.compute_calibration(
        cache,
        n_trials=3,
        bank_b=5,
        seed=42,
        workers=6,
        backend="serial",
        checkpoint_path=checkpoint,
        benchmark_only=False,
    )
    assert len(second["trial_details"]) == 3
    assert calls["n"] == 0
