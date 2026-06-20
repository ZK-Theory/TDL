"""Contract bindings for T-STRAND-1 STRAND vs W2/landscape comparison output."""

from __future__ import annotations

import copy
import glob
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajectory_tda.discovery.strand_comparison import validate_strand_comparison_output

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
SCHEMA_CONTRACT = "discovery-harness/strand-comparison-output.yaml"
VALIDATION_CONTRACT = "discovery-harness/strand-comparison-output-json-validation.yaml"


def _load_contract(rel_path: str) -> dict[str, Any]:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _valid_payload() -> dict[str, Any]:
    """Minimal conforming payload matching the strand-comparison-output contract."""
    return {
        "schema_version": "strand-comparison/v1",
        "generated_at": "2026-06-17T12:00:00+00:00",
        "task": "T-STRAND-1: STRAND vs W2/landscape testing comparison (toy scale)",
        "pre_registration": ("results/trajectory_tda_strand/comparison/pre_registrations_2026-06-17.json"),
        "inputs": {
            "git_head": "abc1234",
            # Synthetic relative placeholders — the validator only checks these
            # are present strings, never opens them; keep machine paths out.
            "bhps_frozen_cache": (
                "results/trajectory_tda_integration/stage1/cache/"
                "null_diagrams_bhps_frozen_B1000_L5000_seed42_2026-05-28.npz"
            ),
            "usoc_frozen_cache": (
                "results/trajectory_tda_integration/stage1/cache/"
                "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz"
            ),
        },
        "params": {
            "finite_lifetimes_only": True,
            "grid_size_g": 25,
            "null_model": "label-permutation",
            "B": 1000,
            "B_baseline_pairs": 200,
            "baseline_null": "cross null-null",
            "baseline_sidedness": "one-sided (observed >= null)",
            "p_value_formula": "(r+1)/(B+1)",
            "two_sided": True,
            "n_calibration_trials": 100,
            "frozen_loadings": True,
            "L": 5000,
            "seed": 42,
            "alpha_level": 0.05,
        },
        "null_non_invariance": {
            "h0": {"observed_stat": 1.23, "perm_stats_sample": [0.5, 0.8], "non_invariant": True},
            "h1": {"observed_stat": 0.95, "perm_stats_sample": [0.3, 0.6], "non_invariant": True},
        },
        "calibration": {
            "ks_statistic": 0.08,
            "ks_p": 0.42,
            "mean_pvalue": 0.51,
            "calibrated": True,
        },
        "comparison": {
            "h0": {
                "strand_logrank_p": 0.03,
                "strand_logrank_stat": 2.1,
                "strand_f_logrank_p": 0.04,
                "strand_f_logrank_stat": 1.9,
                "w2_p": 0.02,
                "w2_obs": 0.15,
                "landscape_l2_p": 0.05,
                "landscape_l2_obs": 0.3,
                "localisation": {
                    "quantile_33": 0.1,
                    "quantile_67": 0.3,
                    "bhps": {"short": 100, "medium": 120, "long": 80},
                    "usoc": {"short": 110, "medium": 130, "long": 90},
                    "interpretation": "test",
                },
                "strand_perm_stats": [0.5, 1.0],
                "null_w2_dist": [0.1, 0.2],
                "null_land_dist": [0.2, 0.3],
            },
            "h1": {
                "strand_logrank_p": 0.2,
                "strand_logrank_stat": 0.8,
                "strand_f_logrank_p": 0.25,
                "strand_f_logrank_stat": 0.7,
                "w2_p": 0.15,
                "w2_obs": 0.12,
                "landscape_l2_p": 0.18,
                "landscape_l2_obs": 0.25,
                "localisation": {
                    "quantile_33": 0.05,
                    "quantile_67": 0.15,
                    "bhps": {"short": 50, "medium": 60, "long": 40},
                    "usoc": {"short": 55, "medium": 65, "long": 45},
                    "interpretation": "test",
                },
                "strand_perm_stats": [0.3, 0.9],
                "null_w2_dist": [0.08, 0.11],
                "null_land_dist": [0.1, 0.2],
            },
        },
        "decision": {
            "verdict": "additive",
            "rationale": "STRAND calibrated and adds localisation.",
        },
        "wall_time_seconds": 42.0,
    }


def _mutated(path: tuple[str, ...], value: object) -> dict[str, Any]:
    """Return a deep copy of the valid payload with one field changed."""
    payload = copy.deepcopy(_valid_payload())
    target = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    return payload


# ---------------------------------------------------------------------------
# Primary contract binding test (named in contract binding.test_function)
# ---------------------------------------------------------------------------


def test_strand_comparison_schema_rejects_invalid_payloads() -> None:
    """Conforming payload passes; contract-listed violations reject."""
    # Valid payload passes
    validate_strand_comparison_output(_valid_payload())

    # (a) calibrated disagrees with ks_p >= 0.05
    bad = _mutated(("calibration", "calibrated"), False)  # ks_p=0.42 -> should be True
    with pytest.raises(ValueError, match="disagrees"):
        validate_strand_comparison_output(bad)

    bad = _mutated(("calibration", "ks_p"), 0.01)  # ks_p<0.05 but calibrated=True
    with pytest.raises(ValueError, match="disagrees"):
        validate_strand_comparison_output(bad)

    # (b) p-values outside [0, 1]
    bad = _mutated(("comparison", "h0", "strand_logrank_p"), 1.5)
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        validate_strand_comparison_output(bad)

    bad = _mutated(("comparison", "h1", "w2_p"), -0.1)
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        validate_strand_comparison_output(bad)

    bad = _mutated(("calibration", "ks_p"), -0.01)
    with pytest.raises(ValueError):
        validate_strand_comparison_output(bad)

    # (c) verdict-calibration coupling violated
    # miscalibrated verdict when calibrated=True
    bad = _mutated(("decision", "verdict"), "miscalibrated")
    # calibration.calibrated is True in valid payload
    with pytest.raises(ValueError, match="calibrated result must have verdict"):
        validate_strand_comparison_output(bad)

    # additive verdict when calibrated=False (miscalibrated)
    bad = copy.deepcopy(_valid_payload())
    bad["calibration"]["ks_p"] = 0.01
    bad["calibration"]["calibrated"] = False
    bad["decision"]["verdict"] = "additive"
    with pytest.raises(ValueError, match="miscalibrated"):
        validate_strand_comparison_output(bad)

    # (d) forbidden refit keys
    bad = copy.deepcopy(_valid_payload())
    bad["refit_pca"] = True
    with pytest.raises(ValueError, match="Forbidden"):
        validate_strand_comparison_output(bad)

    bad = copy.deepcopy(_valid_payload())
    bad["per_call_loadings"] = True
    with pytest.raises(ValueError, match="Forbidden"):
        validate_strand_comparison_output(bad)

    # (e) missing required key
    bad = copy.deepcopy(_valid_payload())
    del bad["calibration"]
    with pytest.raises(ValueError, match="Missing required keys"):
        validate_strand_comparison_output(bad)

    # (f) null_non_invariance must assert non_invariant == true per dimension
    bad = _mutated(("null_non_invariance", "h0", "non_invariant"), False)
    with pytest.raises(ValueError, match="non_invariant must be true"):
        validate_strand_comparison_output(bad)


# ---------------------------------------------------------------------------
# Output JSON validation test
# ---------------------------------------------------------------------------


def test_strand_comparison_output_json_validation() -> None:
    """Every committed strand_vs_baseline_*.json passes the schema contract."""
    pattern = str(REPO_ROOT / "results/trajectory_tda_strand/comparison/strand_vs_baseline_*.json")
    result_files = glob.glob(pattern)
    if not result_files:
        pytest.skip("No strand_vs_baseline_*.json files found; run after compute.")
    for path in result_files:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        validate_strand_comparison_output(payload)


# ---------------------------------------------------------------------------
# Contract metadata binding tests
# ---------------------------------------------------------------------------


def test_strand_comparison_schema_contract_metadata() -> None:
    """Schema contract file has the expected metadata."""
    contract = _load_contract(SCHEMA_CONTRACT)
    assert contract["id"] == "strand-comparison-output"
    assert contract["kind"] == "schema"
    assert contract["pending"] is False
    binding = contract["binding"]
    assert binding["test_file"] == "tests/discovery/test_strand_comparison_contract.py"
    assert binding["test_function"] == "test_strand_comparison_schema_rejects_invalid_payloads"

    required_names = [entry["name"] for entry in contract["schema_def"]["required_keys"]]
    assert "schema_version" in required_names
    assert "calibration" in required_names
    assert "comparison" in required_names
    assert "decision" in required_names
    assert "null_non_invariance" in required_names

    forbidden_names = [entry["name"] for entry in contract["schema_def"]["forbidden_keys"]]
    assert "refit_pca" in forbidden_names
    assert "per_call_loadings" in forbidden_names


def test_strand_comparison_json_validation_contract_metadata() -> None:
    """JSON-validation contract file has expected metadata."""
    contract = _load_contract(VALIDATION_CONTRACT)
    assert contract["id"] == "strand-comparison-output-json-validation"
    assert contract["kind"] == "output_validation"
    assert contract["pending"] is False
    # schema_contracts is nested under the output_validation key in the YAML.
    assert "strand-comparison-output" in contract["output_validation"]["schema_contracts"]


# ---------------------------------------------------------------------------
# Params validation tests
# ---------------------------------------------------------------------------


def test_params_validation_gates() -> None:
    """Required params values are enforced."""
    # finite_lifetimes_only must be True
    bad = _mutated(("params", "finite_lifetimes_only"), False)
    with pytest.raises(ValueError, match="finite_lifetimes_only"):
        validate_strand_comparison_output(bad)

    # frozen_loadings must be True
    bad = _mutated(("params", "frozen_loadings"), False)
    with pytest.raises(ValueError, match="frozen_loadings"):
        validate_strand_comparison_output(bad)

    # grid_size_g must be 25
    bad = _mutated(("params", "grid_size_g"), 50)
    with pytest.raises(ValueError, match="grid_size_g"):
        validate_strand_comparison_output(bad)

    # B must be >= 1000
    bad = _mutated(("params", "B"), 999)
    with pytest.raises(ValueError, match="params.B"):
        validate_strand_comparison_output(bad)

    # seed must be 42
    bad = _mutated(("params", "seed"), 0)
    with pytest.raises(ValueError, match="seed"):
        validate_strand_comparison_output(bad)

    # L must be 5000
    bad = _mutated(("params", "L"), 1000)
    with pytest.raises(ValueError, match="params.L"):
        validate_strand_comparison_output(bad)


# ---------------------------------------------------------------------------
# Log-rank vectorisation equivalence (Manager perf fix, 2026-06-17)
# ---------------------------------------------------------------------------


def test_log_rank_vectorised_matches_reference_loop() -> None:
    """Vectorised O(n log n) log-rank equals the O(n^2) reference loop.

    Guards the 2026-06-17 performance amendment: the public
    ``log_rank_statistic`` was vectorised from the original loop; the statistic
    must be identical (incl. tied event times).
    """
    import numpy as np

    from trajectory_tda.discovery.strand_comparison import (
        _log_rank_statistic_loop,
        log_rank_statistic,
    )

    rng = np.random.RandomState(0)
    for _ in range(100):
        n_a = int(rng.randint(1, 60))
        n_b = int(rng.randint(1, 60))
        decimals = int(rng.choice([1, 2, 8]))  # coarse rounding forces ties
        a = np.round(rng.exponential(1.0, n_a), decimals)
        b = np.round(rng.exponential(1.0, n_b), decimals)
        assert abs(log_rank_statistic(a, b) - _log_rank_statistic_loop(a, b)) < 1e-9

    # Empty-group guard returns 0.0.
    assert log_rank_statistic(np.array([]), np.array([1.0, 2.0])) == 0.0
