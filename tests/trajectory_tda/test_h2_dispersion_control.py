# Research context: Stage-1 H2 dispersion-control confirmatory diagnostic.
# Purpose: Bind median-pdist normalization and dual-metric H2 aggregation.
"""Tests for the H2 dispersion-control dual-metric diagnostic."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from poverty_tda.topology.multidim_ph import PHResult, compute_rips_ph
import trajectory_tda.scripts.run_h2_dispersion_dualmetric as diagnostic


def _icosahedron_cloud() -> np.ndarray:
    phi = (1.0 + np.sqrt(5.0)) / 2.0
    return np.asarray(
        [
            (0, 1, phi),
            (0, -1, phi),
            (0, 1, -phi),
            (0, -1, -phi),
            (1, phi, 0),
            (-1, phi, 0),
            (1, -phi, 0),
            (-1, -phi, 0),
            (phi, 0, 1),
            (-phi, 0, 1),
            (phi, 0, -1),
            (-phi, 0, -1),
        ],
        dtype=np.float64,
    )


def _finite_h2(ph: PHResult) -> np.ndarray:
    return diagnostic._finite_dgm_from_ph(ph, 2)


def _sorted_dgm(dgm: np.ndarray) -> np.ndarray:
    if dgm.shape[0] == 0:
        return dgm
    order = np.lexsort((dgm[:, 1], dgm[:, 0]))
    return dgm[order]


@pytest.mark.parametrize("normalizer", ["median-pdist", "max-pdist", "mean-pdist"])
def test_normalize_landmarks_by_pairwise_scale_returns_unit_scale(normalizer: diagnostic.LandmarkNormalizer) -> None:
    cloud = _icosahedron_cloud() * 3.0

    normalized, scale = diagnostic._normalize_landmarks(cloud, normalizer)

    assert scale > 0.0
    assert diagnostic._pairwise_distance_scale(normalized, normalizer) == pytest.approx(1.0)
    assert normalized.shape == cloud.shape


def test_normalize_landmarks_by_median_pdist_wrapper_returns_unit_median() -> None:
    cloud = _icosahedron_cloud() * 3.0

    normalized, scale = diagnostic._normalize_landmarks_by_median_pdist(cloud)

    assert scale > 0.0
    assert diagnostic._median_pairwise_distance(normalized) == pytest.approx(1.0)


@pytest.mark.parametrize("normalizer", ["median-pdist", "max-pdist", "mean-pdist"])
def test_h2_dispersion_normalization_scale_invariance_contract(
    normalizer: diagnostic.LandmarkNormalizer,
) -> None:
    """Contract binding: normalized H2 diagrams and metrics ignore global rescaling."""
    base = _icosahedron_cloud()
    null = base.copy()
    null[:, 2] *= 0.8

    null_norm, _ = diagnostic._normalize_landmarks(null, normalizer)
    ph_null = compute_rips_ph(null_norm, max_dim=2, do_cocycles=False, method="ripser")
    null_h2 = _finite_h2(ph_null)

    ref_norm, _ = diagnostic._normalize_landmarks(base, normalizer)
    ph_ref = compute_rips_ph(ref_norm, max_dim=2, do_cocycles=False, method="ripser")
    ref_h2 = _finite_h2(ph_ref)
    assert ref_h2.shape[0] >= 1

    ref_w2 = diagnostic._wasserstein_between_diagrams(ref_h2, null_h2, 2)
    ref_landscape = diagnostic._landscape_l2_between_diagrams(ref_h2, null_h2, k_max=5, n_points=200)

    for scale_factor in (0.5, 2.0):
        scaled_norm, _ = diagnostic._normalize_landmarks(base * scale_factor, normalizer)
        ph_scaled = compute_rips_ph(scaled_norm, max_dim=2, do_cocycles=False, method="ripser")
        scaled_h2 = _finite_h2(ph_scaled)

        assert scaled_h2.shape == ref_h2.shape
        assert np.max(np.abs(_sorted_dgm(scaled_h2) - _sorted_dgm(ref_h2))) <= 1e-6
        assert diagnostic._wasserstein_between_diagrams(scaled_h2, null_h2, 2) == pytest.approx(ref_w2, abs=1e-6)
        assert diagnostic._landscape_l2_between_diagrams(
            scaled_h2,
            null_h2,
            k_max=5,
            n_points=200,
        ) == pytest.approx(ref_landscape, abs=1e-6)


def test_landscape_l2_between_diagrams_is_symmetric_on_union_grid() -> None:
    dgm_a = np.asarray([[0.0, 1.0]], dtype=np.float64)
    dgm_b = np.asarray([[2.0, 4.0], [2.5, 3.5]], dtype=np.float64)

    ab = diagnostic._landscape_l2_between_diagrams(dgm_a, dgm_b, k_max=5, n_points=200)
    ba = diagnostic._landscape_l2_between_diagrams(dgm_b, dgm_a, k_max=5, n_points=200)

    assert ab > 0.0
    assert ab == pytest.approx(ba, abs=1e-12)


def test_aggregate_h2_dual_metric_uses_b_plus_one_pvalue_and_keeps_distributions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    null_results = [
        {"H2": 4.0, "H2_dgm": [[0.0, 0.2]]},
        {"H2": 4.0, "H2_dgm": [[0.0, 0.3]]},
        {"H2": 4.0, "H2_dgm": [[0.0, 0.4]]},
        {"H2": 4.0, "H2_dgm": [[0.0, 0.5]]},
    ]
    ph_obs = PHResult(dgms={2: np.asarray([[0.0, 1.0]], dtype=np.float64)})

    monkeypatch.setattr(diagnostic, "_draw_null_pairs", lambda n_permutations, seed, cap: [(0, 1), (1, 2), (2, 3)])
    monkeypatch.setattr(diagnostic, "_wasserstein_between_diagrams", lambda dgm_a, dgm_b, dim: 1.0)

    def fake_landscape_l2(observed_dgm, comparison_dgm, **kwargs):
        return 4.0 if np.isclose(float(observed_dgm[0, 1]), 1.0) else 1.0

    monkeypatch.setattr(diagnostic, "_landscape_l2_between_diagrams", fake_landscape_l2)

    result = diagnostic._aggregate_h2_dual_metric(
        null_results,
        ph_obs,
        seed=42,
        n_null_pairs_cap=2,
        k_max=5,
        n_points=200,
    )

    assert result["w2"]["effect_null_pairs"] == 2
    assert result["w2"]["pvalue_null_draws"] == 3
    assert result["w2"]["p_value"] == pytest.approx(1 / 4)
    assert result["landscape_l2"]["p_value"] == pytest.approx(1 / 4)
    assert len(result["w2"]["obs_null_distribution"]) == 4
    assert len(result["w2"]["null_null_distribution"]) == 2
    assert len(result["pair_indices"]) == 2
    assert len(result["pvalue_pair_indices"]) == 3


def test_decision_branch_escalates_on_either_normalized_metric() -> None:
    base_cell = {
        "normalized": {
            "L": 200,
            "metrics": {
                "H2": {
                    "w2": {"p_value": 0.1},
                    "landscape_l2": {"p_value": 0.2},
                }
            },
        }
    }
    assert diagnostic._decision_branch({"L200": base_cell}, alpha=0.05)["branch"] == "restriction_stands"

    rejecting = {
        "normalized": {
            "L": 300,
            "metrics": {
                "H2": {
                    "w2": {"p_value": 0.1},
                    "landscape_l2": {"p_value": 0.01},
                }
            },
        }
    }
    decision = diagnostic._decision_branch({"L300": rejecting}, alpha=0.05)
    assert decision["branch"] == "stop_and_escalate"
    assert decision["rejecting_normalized_cells"] == [
        {
            "L": 300,
            "w2_p_value": 0.1,
            "landscape_l2_p_value": 0.01,
            "w2_rejects": False,
            "landscape_l2_rejects": True,
        }
    ]


def _characterization_cell(
    *,
    L: int,
    obs_birth: float,
    null_birth: float,
    obs_death: float,
    null_death: float,
    w2_p: float,
    land_p: float,
) -> dict:
    return {
        "L": L,
        "observed": {"h2_birth_death": {"birth_median": obs_birth, "death_median": obs_death}},
        "null_h2_birth_death": {
            "birth_median_summary": {"median": null_birth},
            "death_median_summary": {"median": null_death},
        },
        "metrics": {
            "H2": {
                "w2": {"p_value": w2_p, "t_ratio": 1.5},
                "landscape_l2": {"p_value": land_p, "t_ratio": 1.6},
            }
        },
    }


def test_characterization_decision_requires_power_and_consistent_normalizer_direction() -> None:
    robust = {
        "median-pdist": _characterization_cell(
            L=200,
            obs_birth=0.6,
            null_birth=0.7,
            obs_death=0.62,
            null_death=0.72,
            w2_p=0.005,
            land_p=0.004,
        ),
        "max-pdist": _characterization_cell(
            L=200,
            obs_birth=0.4,
            null_birth=0.5,
            obs_death=0.42,
            null_death=0.52,
            w2_p=0.02,
            land_p=0.02,
        ),
        "mean-pdist": _characterization_cell(
            L=200,
            obs_birth=0.9,
            null_birth=0.8,
            obs_death=0.92,
            null_death=0.82,
            w2_p=0.02,
            land_p=0.02,
        ),
    }

    decision = diagnostic._characterization_decision({"L200": robust}, alpha=0.05, power_alpha=0.01)

    assert decision["branch"] == "restriction_stands"
    assert decision["per_L"][0]["sign_flip_count"] == 1
    assert decision["per_L"][0]["supporting_normalizer_count"] == 2

    robust["mean-pdist"] = _characterization_cell(
        L=200,
        obs_birth=0.6,
        null_birth=0.7,
        obs_death=0.62,
        null_death=0.72,
        w2_p=0.02,
        land_p=0.02,
    )
    decision = diagnostic._characterization_decision({"L200": robust}, alpha=0.05, power_alpha=0.01)

    assert decision["branch"] == "stop_and_escalate"
    assert decision["robust_L_values"] == [200]


def test_run_condition_passes_normalization_flag_to_null_worker(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    seen: dict[str, object] = {}
    args = SimpleNamespace(
        B=1,
        seed=42,
        n_jobs=1,
        ph_timeout_seconds=10.0,
        h2_tetra_budget=1e9,
        resume=False,
        verbose_joblib=False,
        landscape_k_max=5,
        landscape_n_points=200,
        n_null_pairs_cap=1,
        max_hours=0.0,
    )
    ph_obs = PHResult(dgms={2: np.asarray([[0.0, 1.0]], dtype=np.float64)})

    monkeypatch.setattr(diagnostic, "_compute_observed_ph", lambda *args, **kwargs: (ph_obs, {}, 2.0, 0.1))
    monkeypatch.setattr(
        diagnostic,
        "_run_condition_permutation",
        lambda index, **kwargs: (
            seen.setdefault("normalize", kwargs["normalize"])
            and seen.setdefault("normalizer", kwargs["normalizer"])
            and index,
            {"H2": 0.5, "H2_dgm": [[0.0, 0.1]], "_ph_provenance": {}, "_wall_time_seconds": 0.01},
            0.01,
        ),
    )
    monkeypatch.setattr(
        diagnostic,
        "_aggregate_h2_dual_metric",
        lambda *args, **kwargs: {
            "dim": "H2",
            "w2": {"p_value": 1.0, "mean_obs_null": 0.5},
            "landscape_l2": {"p_value": 1.0},
        },
    )

    diagnostic._run_condition(
        args=args,
        condition="normalized",
        B=1,
        normalizer="mean-pdist",
        embeddings=np.zeros((3, 2)),
        trajectories=[["EL", "EM"], ["EM", "EH"], ["EH", "EL"]],
        embed_kwargs={},
        frozen_models={},
        obs_landmarks=np.asarray([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float64),
        checkpoint_dir=tmp_path,
    )

    assert seen["normalize"] is True
    assert seen["normalizer"] == "mean-pdist"
