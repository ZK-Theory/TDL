import random
from pathlib import Path

import numpy as np
import pytest

from trajectory_tda.analysis.panel.fixed_margin_max_ari import (
    achievable_max_table,
    certify_max_ari,
    concentration_upper_bound_sumsq,
)
from trajectory_tda.analysis.panel.t123b_ari_om_gmm import (
    CANARY_OBSERVED_ARI,
    EXPECTED_N,
    GMM_K,
    OM_K,
    dispatch_t123b_json,
    validate_ari_om_gmm_output,
)


def _brute_force_max_sumsq(row_counts: list[int], col_counts: list[int]) -> int:
    """Exhaustive maximum of Sum n_ij**2 over the fixed-margin integer polytope."""

    n_rows, n_cols = len(row_counts), len(col_counts)
    best = [-1]

    def place_row(i: int, caps: list[int], acc: int) -> None:
        if i == n_rows:
            if all(x == 0 for x in caps) and acc > best[0]:
                best[0] = acc
            return

        def split(j: int, rem: int, a: int, c: list[int]) -> None:
            if j == n_cols:
                if rem == 0:
                    place_row(i + 1, c, a)
                return
            for v in range(0, min(rem, c[j]) + 1):
                nxt = c[:]
                nxt[j] -= v
                split(j + 1, rem - v, a + v * v, nxt)

        split(0, row_counts[i], acc, caps[:])

    place_row(0, col_counts[:], 0)
    return best[0]


def test_fixed_margin_max_is_certified_not_vacuous():
    """The B9 OM/GMM margins yield a real bracket (< 1.0), not the trivial 1.0."""

    om = np.array([3438, 2086, 2949, 2489, 9003, 1775, 5540], dtype=np.int64)
    gmm = np.array([3787, 7358, 5415, 3333, 3510, 1813, 2064], dtype=np.int64)
    cert = certify_max_ari(om, gmm, CANARY_OBSERVED_ARI)

    # The achievable maximum is a real constrained maximum strictly below 1.0,
    # so the normalisation is not vacuous (regression guard on the old 1.0 bug).
    assert cert.status == "bracket"
    assert cert.ari_max_achievable < 1.0
    assert cert.ari_max_upper_bound >= cert.ari_max_achievable
    assert cert.normalised_observed_ari > CANARY_OBSERVED_ARI
    # The achieving table is feasible: its margins reproduce the inputs.
    table = cert.achieving_table
    assert np.array_equal(table.sum(axis=1), om)
    assert np.array_equal(table.sum(axis=0), gmm)
    # Pair-overlap of the table matches the reported achievable value, and the
    # concentration upper bound dominates it.
    sumsq = int((table.astype(np.int64) ** 2).sum())
    assert (sumsq - int(om.sum())) // 2 == cert.achievable_pair_overlap
    assert concentration_upper_bound_sumsq(om, gmm) >= sumsq


def test_fixed_margin_max_matches_brute_force_on_small_instances():
    """achievable_max_table attains the true maximum and the UB is valid (k<=6)."""

    rng = random.Random(20260624)
    for _ in range(200):
        n_rows = rng.randint(2, 4)
        n_cols = rng.randint(2, 4)
        total = rng.randint(n_cols, 11)
        cuts = sorted(rng.randint(0, total) for _ in range(n_rows - 1))
        prev = 0
        rows = []
        for x in cuts:
            rows.append(x - prev)
            prev = x
        rows.append(total - prev)
        cuts = sorted(rng.randint(0, total) for _ in range(n_cols - 1))
        prev = 0
        cols = []
        for x in cuts:
            cols.append(x - prev)
            prev = x
        cols.append(total - prev)

        brute = _brute_force_max_sumsq(rows, cols)
        table = achievable_max_table(np.array(rows), np.array(cols))
        achieved = int((table.astype(np.int64) ** 2).sum())
        ub = concentration_upper_bound_sumsq(np.array(rows), np.array(cols))
        assert achieved == brute, f"achievable {achieved} != brute {brute} for {rows},{cols}"
        assert ub >= brute, f"upper bound {ub} < brute max {brute} for {rows},{cols}"


def test_ari_om_gmm_normalisation_output_schema():
    payload = _om_payload()
    validate_ari_om_gmm_output(payload)

    # (a) schema_version must be the OM-vs-GMM tag.
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(_mutated("schema_version", "ari-normalisation-v1"))

    # (b) referent must name optimal-matching k=7 vs GMM k=7.
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(_mutated("referent", "H0 tree-cut vs GMM"))

    # (c) input paths and gmm_labels_key must be canonical.
    bad_paths = _om_payload()
    bad_paths["input_paths"]["trajectories"] = "results/other/stale_sequences.json"
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_paths)
    bad_key = _om_payload()
    bad_key["input_paths"]["gmm_labels_key"] = "pickle_labels"
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_key)

    # (d) representation must not use pickle/joblib labels.
    bad_repr = _om_payload()
    bad_repr["representation"]["uses_pickle_or_joblib_labels"] = True
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_repr)

    # (e) locked parameters and label counts.
    bad_om_k = _om_payload()
    bad_om_k["parameters"]["om_k"] = 6
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_om_k)
    bad_gmm_k = _om_payload()
    bad_gmm_k["parameters"]["gmm_k"] = 8
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_gmm_k)
    bad_seed = _om_payload()
    bad_seed["parameters"]["seed"] = 7
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_seed)
    bad_n = _om_payload()
    bad_n["label_counts"]["om_label_length"] = EXPECTED_N - 1
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_n)
    bad_cluster_count = _om_payload()
    bad_cluster_count["label_counts"]["om_cluster_count"] = 6
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_cluster_count)

    # (f) observed_ari must be in range and reproduce the canary.
    bad_range = _om_payload()
    bad_range["observed_ari"] = 1.5
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_range)
    bad_canary = _om_payload()
    bad_canary["observed_ari"] = 0.40
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_canary)

    # (g) null se sign and bootstrap CI ordering.
    bad_null = _om_payload()
    bad_null["null_distribution"]["se"] = -0.1
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_null)
    bad_ci = _om_payload()
    bad_ci["bootstrap_ci"]["percentile_95"] = [0.30, 0.10]
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_ci)

    # (h) exact / status logic must be consistent and the upper bound must
    #     dominate the achievable value.
    bad_status = _om_payload()
    bad_status["max_achievable_ari"]["status"] = "upper_bound"
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_status)
    bad_exact_flag = _om_payload()
    bad_exact_flag["max_achievable_ari"]["exact"] = True  # exact True but status "bracket"
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_exact_flag)
    bad_ub = _om_payload()
    bad_ub["max_achievable_ari"]["rigorous_upper_bound"]["ari"] = 0.50  # below value 0.84
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_ub)

    # (j) max_achievable_ari.value must be a real fixed-margin maximum < 1.0,
    #     never the vacuous 1.0 the trivial fallback produced.
    bad_vacuous = _om_payload()
    bad_vacuous["max_achievable_ari"]["value"] = 1.0
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_vacuous)

    # (k) the normalised ARI must differ from the observed ARI (a real
    #     maximum < 1 strictly rescales it upward).
    bad_norm = _om_payload()
    bad_norm["max_achievable_ari"]["normalised_observed_ari"] = bad_norm["observed_ari"]
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_norm)

    # (i) forbidden keys (object-confusion guard versus T1.23).
    bad_eps = _om_payload()
    bad_eps["eps_star"] = 0.54
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_eps)
    bad_h0 = _om_payload()
    bad_h0["h0_components"] = {"n_components": 2}
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_h0)
    bad_pickle = _om_payload()
    bad_pickle["pickle_labels_path"] = "old.pkl"
    with pytest.raises(ValueError):
        validate_ari_om_gmm_output(bad_pickle)


def test_ari_om_gmm_normalisation_json_validation_dispatch():
    payload = _om_payload()
    # OM-vs-GMM files are routed to the schema validator.
    assert dispatch_t123b_json(
        Path("results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-22.json"),
        payload,
    )
    with pytest.raises(ValueError):
        dispatch_t123b_json(
            Path("results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-22.json"),
            _mutated("schema_version", "wrong"),
        )
    # (b) The H0-tree-cut ari_normalised_*.json file is NOT captured.
    assert not dispatch_t123b_json(
        Path("results/panel_methodology/ari/ari_normalised_2026-06-06.json"),
        {"schema_version": "ari-normalisation-v1"},
    )
    # The superseded legacy 2026-06-23 file is grandfathered out of validation
    # (its vacuous max_achievable_ari is replaced by the 2026-06-24 file).
    assert not dispatch_t123b_json(
        Path("results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-23.json"),
        {"schema_version": "anything"},
    )
    # Other panel methodology JSONs are NOT captured.
    assert not dispatch_t123b_json(
        Path("results/panel_methodology/regression/tier2_svyglm_headline_2026-06-03.json"),
        {"schema_version": "unrelated"},
    )


def _mutated(key, value):
    payload = _om_payload()
    payload[key] = value
    return payload


def _om_payload():
    return {
        "schema_version": "ari-om-gmm-normalisation-v1",
        "created_at": "2026-06-22",
        "git_head": "abc123",
        "referent": ("optimal-matching (dynamic Hamming, Lesnard 2010) k=7 vs GMM k=7"),
        "input_paths": {
            "trajectories": "results/trajectory_tda_integration/01_trajectories_sequences.json",
            "analysis_json": "results/trajectory_tda_integration/05_analysis.json",
            "gmm_labels_key": "gmm_labels",
        },
        "representation": {
            "om_label_source": "fcluster(k=7) of Ward linkage (dynamic Hamming)",
            "gmm_label_source": "canonical 05_analysis.json['gmm_labels']",
            "om_baseline_directory": "results/trajectory_tda_robustness/om_baseline",
            "row_alignment": "same trajectory/GMM row order, both length 27,280",
            "uses_pickle_or_joblib_labels": False,
            "regenerated_linkage": True,
        },
        "parameters": {
            "om_k": OM_K,
            "gmm_k": GMM_K,
            "om_distance": "dynamic Hamming distance (Lesnard 2010), Ward linkage",
            "seed": 42,
            "null_B_requested": 5000,
            "bootstrap_B_requested": 1000,
            "n_jobs": 8,
        },
        "label_counts": {
            "n": EXPECTED_N,
            "om_label_length": EXPECTED_N,
            "gmm_label_length": EXPECTED_N,
            "om_cluster_count": OM_K,
            "om_cluster_counts": {str(i): EXPECTED_N // OM_K for i in range(OM_K)},
            "gmm_regime_count": GMM_K,
            "gmm_regime_counts": {str(i): EXPECTED_N // GMM_K for i in range(GMM_K)},
        },
        "observed_ari": CANARY_OBSERVED_ARI,
        "null_distribution": {
            "procedure": "Permute GMM labels relative to fixed OM k=7 labels.",
            "B": 5000,
            "seed": 42,
            "finite_count": 5000,
            "failures_non_finite": 0,
            "mean": 0.0,
            "se": 0.0009,
            "pvalue": 0.0002,
            "pvalue_definition": "(r + 1) / (B + 1)",
            "exceedances_observed_or_larger": 0,
            "quantiles": {"0.025": -0.001, "0.5": 0.0, "0.975": 0.001},
        },
        "max_achievable_ari": {
            "value": 0.84,
            "exact": False,
            "status": "bracket",
            "method": "deterministic NW + 2-opt achievable construction",
            "achievable_lower_bound": {
                "ari": 0.84,
                "pair_overlap_sum": 59684973,
                "method": "deterministic NW + 2-opt achievable construction",
            },
            "rigorous_upper_bound": {
                "ari": 0.86,
                "pair_overlap_sum": 60862048,
                "method": "per-line concentration relaxation",
            },
            "achieving_table": [[EXPECTED_N // (OM_K * GMM_K)] * GMM_K for _ in range(OM_K)],
            "normalised_observed_ari": CANARY_OBSERVED_ARI / 0.84,
            "normalised_ari_bracket": [CANARY_OBSERVED_ARI / 0.86, CANARY_OBSERVED_ARI / 0.84],
            "normalised_ci_percentile_95": [0.303, 0.320],
        },
        "bootstrap_ci": {
            "procedure": "Resample paired individual rows (OM label, GMM label).",
            "resampling_unit": "individual",
            "B": 1000,
            "seed": 42,
            "finite_count": 1000,
            "failures_non_finite": 0,
            "mean": 0.261,
            "se": 0.004,
            "percentile_95": [0.253, 0.269],
        },
        "interpretation": {
            "statistic_role": "descriptive clustering-agreement statistic",
            "closes_b9": True,
            "claim": "OM k=7 and GMM k=7 agree at ARI = 0.26 (closes B9).",
            "causal_claim": "none",
            "topological_distinctiveness_claim": "none",
            "normalisation_basis": "exact",
            "paper_claim_guardrail": "Report only as OM-vs-GMM agreement.",
        },
        "runtime": {"wall_seconds": 12.0},
    }
