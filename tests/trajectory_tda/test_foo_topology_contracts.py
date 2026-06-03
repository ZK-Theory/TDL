# Research context: contracts/manifests/T1.33.yaml
# Purpose: Binding tests for family-of-origin topology signature construction
#   and output schemas.
"""Contract bindings for T1.33 FOO topology outputs."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.scripts import run_foo_topology_signature as foo


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"


def _load_contract(rel_path: str) -> dict:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _required_root_keys(schema_rel_path: str) -> list[str]:
    contract = _load_contract(schema_rel_path)
    return [entry["name"] for entry in contract["schema_def"]["required_keys"]]


def _forbidden_root_keys(schema_rel_path: str) -> list[str]:
    contract = _load_contract(schema_rel_path)
    return [entry["name"] for entry in contract["schema_def"].get("forbidden_keys", [])]


def _assert_has_keys(scope: dict, keys: list[str], label: str) -> None:
    missing = [key for key in keys if key not in scope]
    assert not missing, f"{label} missing required keys: {missing}"


def _assert_no_forbidden(scope: dict, keys: list[str], label: str) -> None:
    present = [key for key in keys if key in scope]
    assert not present, f"{label} contains forbidden keys: {present}"


def _assert_per_individual_features_contract(data: dict) -> None:
    _assert_has_keys(
        data,
        _required_root_keys("foo-topology-schemas/per-individual-local-features-output.yaml"),
        "per-individual features root",
    )
    assert data["schema_version"] == foo.SCHEMA_FEATURES
    params = data["params"]
    assert params["k_grid"] == [10, 20, 50]
    assert params["k_primary"] == 20
    assert params["embedding_dim"] == 90
    assert data["input_provenance"]["embeddings_shape"] == [params["n_individuals"], 90]
    for key in ("embeddings_sha256", "foo_clusters_sha256"):
        assert key in data["input_provenance"]
        assert len(data["input_provenance"][key]) == 64
    for k in params["k_grid"]:
        rows = data["features_per_k"][f"k_{k}"]
        assert len(rows) == params["n_individuals"]
        for row in rows:
            for feature in foo.FEATURE_NAMES:
                assert row[feature] >= 0.0


def _assert_sibling_contract(data: dict) -> None:
    _assert_has_keys(
        data,
        _required_root_keys("foo-topology-schemas/sibling-pair-permutation-output.yaml"),
        "sibling permutation root",
    )
    _assert_no_forbidden(
        data,
        _forbidden_root_keys("foo-topology-schemas/sibling-pair-permutation-output.yaml"),
        "sibling permutation root",
    )
    params = data["params"]
    assert params["B"] == 5000
    assert params["pvalue_formula"] == "(r+1)/(B+1)"
    assert params["pvalue_null_draws"] == params["B"]
    samples = data["null_distribution"]["mean_within_pair_distance_samples"]
    assert len(samples) == params["B"]
    observed = data["observed"]["mean_within_pair_distance"]
    r = sum(1 for sample in samples if sample <= observed)
    assert data["permutation_pvalue"] == pytest.approx((r + 1) / (params["B"] + 1))
    assert set(data["per_feature_icc"]) == set(foo.FEATURE_NAMES)
    for values in data["per_feature_icc"].values():
        assert 0.0 <= values["point_estimate"] <= 1.0
        assert 0.0 <= values["bootstrap_ci_lower"] <= 1.0
        assert 0.0 <= values["bootstrap_ci_upper"] <= 1.0
        assert values["bootstrap_B"] == 1000


def _assert_comparison_contract(data: dict) -> None:
    _assert_has_keys(
        data,
        _required_root_keys("foo-topology-schemas/topology-distinctiveness-comparison-output.yaml"),
        "comparison root",
    )
    _assert_no_forbidden(
        data,
        _forbidden_root_keys("foo-topology-schemas/topology-distinctiveness-comparison-output.yaml"),
        "comparison root",
    )
    assert set(data["arms"]) == {
        "topological",
        "c1_bigram_coordinate",
        "c2_summary_trajectory",
    }
    expected_dims = {"topological": 3, "c1_bigram_coordinate": 90, "c2_summary_trajectory": 10}
    for arm_name, arm in data["arms"].items():
        _assert_has_keys(
            arm,
            [
                "feature_dim",
                "permutation_pvalue",
                "effect_size_ratio",
                "n_icc_features",
                "n_icc_ci_above_zero",
                "max_icc",
                "mean_icc",
                "rejects",
            ],
            f"comparison arm {arm_name}",
        )
        assert arm["feature_dim"] == expected_dims[arm_name]
        assert arm["n_icc_features"] == expected_dims[arm_name]
        assert arm["rejects"] == (arm["permutation_pvalue"] < 0.05)
        assert 0.0 <= arm["max_icc"] <= 1.0
        assert 0.0 <= arm["mean_icc"] <= 1.0
    assert data["distinctiveness_verdict"] == foo.distinctiveness_verdict(data["arms"])


def test_per_individual_knn_local_ph_construction() -> None:
    """Local PH uses l2 kNN, index tie-breaks, and non-negative features."""
    embedding = np.array(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
            [2.0, 0.0],
            [0.0, 2.0],
            [2.0, 2.0],
        ],
        dtype=np.float64,
    )
    tied = foo.exact_knn_indices(embedding, index=0, k=3)
    assert tied.tolist() == [1, 2, 3]

    l2_l1_disagreement = np.array(
        [[0.0, 0.0], [1.5, 1.5], [2.2, 0.0], [3.0, 3.0], [4.0, 4.0], [5.0, 5.0]],
        dtype=np.float64,
    )
    assert foo.exact_knn_indices(l2_l1_disagreement, index=0, k=1).tolist() == [1]

    _, _, groups, neighbours = foo.deterministic_neighbour_indices_by_group(embedding, max_k=3)
    for group_id, group in enumerate(groups):
        subcloud_idx = np.concatenate([[group[0]], neighbours[group_id][:3]])
        assert subcloud_idx.shape == (4,)
        assert int(group[0]) in set(subcloud_idx)
        features = foo.local_persistence_features(embedding[subcloud_idx], landscape_n_points=32)
        assert features.shape == (3,)
        assert np.all(np.isfinite(features))
        assert np.all(features >= 0.0)

    first = foo.local_persistence_features(embedding[[0, 1, 2, 3]], landscape_n_points=32)
    second = foo.local_persistence_features(embedding[[4, 1, 2, 3]], landscape_n_points=32)
    assert np.all(first >= 0.0)
    assert np.all(second >= 0.0)


def test_constrained_shuffle_preserves_cluster_size_partition() -> None:
    """Constrained shuffles preserve partition, vary mapping, and reseed exactly."""
    clusters = np.array([0, 1, 2, 3, 3, 4, 4, 5, 5, 5, 6, 6, 6, 6, 6])
    original = foo.cluster_size_partition(clusters)
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    shuffles1 = [foo.constrained_shuffle_clusters(clusters, rng1) for _ in range(200)]
    shuffles2 = [foo.constrained_shuffle_clusters(clusters, rng2) for _ in range(200)]
    assert any(not np.array_equal(shuffled, clusters) for shuffled in shuffles1)
    for a, b in zip(shuffles1, shuffles2, strict=True):
        assert np.array_equal(a, b)
        assert foo.cluster_size_partition(a) == original
        assert len(np.unique(a)) == len(np.unique(clusters))


def test_icc_cluster_bootstrap_construction() -> None:
    """ICC uses cluster-level bootstrap and percentile CIs."""
    clusters = np.repeat(np.arange(5), 4)
    feature = np.array(
        [
            [0.9], [1.0], [1.1], [1.0],
            [1.9], [2.0], [2.1], [2.0],
            [2.9], [3.0], [3.1], [3.0],
            [3.9], [4.0], [4.1], [4.0],
            [4.9], [5.0], [5.1], [5.0],
        ],
        dtype=np.float64,
    )
    means, within = foo._cluster_feature_stats(feature, clusters)
    expected = np.var(means[:, 0], ddof=1) / (np.var(means[:, 0], ddof=1) + np.nanmean(within[:, 0]))
    assert foo._icc_from_cluster_stats(means, within)[0] == pytest.approx(expected)
    assert expected > 0.99

    icc1 = foo.cluster_bootstrap_icc(feature, clusters, ["x"], B_boot=200, seed=42)["x"]
    icc2 = foo.cluster_bootstrap_icc(feature, clusters, ["x"], B_boot=200, seed=42)["x"]
    assert icc1 == icc2
    assert 0.0 <= icc1["point_estimate"] <= 1.0
    assert 0.0 <= icc1["bootstrap_ci_lower"] <= icc1["bootstrap_ci_upper"] <= 1.0
    assert icc1["bootstrap_B"] == 200


def test_constrained_shuffle_cluster_size_invariant() -> None:
    """Cluster-size preservation holds for uniform, skewed, and singleton-heavy inputs."""
    examples = [
        np.repeat(np.arange(6), 3),
        np.array([0, 1, 2, 3, 3, 4, 4, 4, 5, 5, 5, 5, 5]),
        np.array([0, 1, 2, 3, 4, 5, 5, 6, 7, 8, 8]),
    ]
    for seed, clusters in enumerate(examples, start=10):
        rng = np.random.default_rng(seed)
        partition = foo.cluster_size_partition(clusters)
        for _ in range(100):
            shuffled = foo.constrained_shuffle_clusters(clusters, rng)
            assert foo.cluster_size_partition(shuffled) == partition
            assert len(shuffled) == len(clusters)
            assert len(np.unique(shuffled)) == len(np.unique(clusters))


def test_seed_propagation_reproducibility() -> None:
    """Seeded stochastic helpers reproduce bit-identical numerical outputs."""
    features = np.array(
        [[0.0, 0.0], [0.1, 0.0], [1.0, 1.0], [1.1, 1.0], [2.0, 2.0], [2.1, 2.0]],
        dtype=np.float64,
    )
    clusters = np.array([0, 0, 1, 1, 2, 2], dtype=np.int64)
    null1 = foo.constrained_shuffle_null_distribution(features, clusters, B=20, seed=42)
    null2 = foo.constrained_shuffle_null_distribution(features, clusters, B=20, seed=42)
    assert np.array_equal(null1, null2)
    icc1 = foo.cluster_bootstrap_icc(features, clusters, ["x", "y"], B_boot=20, seed=42)
    icc2 = foo.cluster_bootstrap_icc(features, clusters, ["x", "y"], B_boot=20, seed=42)
    assert icc1 == icc2

    source = (REPO_ROOT / "trajectory_tda/scripts/run_foo_topology_signature.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "default_rng":
                assert node.args or node.keywords, "default_rng must be called with an explicit seed"

    params = foo._common_params(seed=42, B=5000, icc_bootstrap_B=1000, n=6)
    assert params["seed"] == 42
    assert params["B"] == 5000
    assert params["icc_bootstrap_B"] == 1000


def test_per_individual_local_features_json_schema() -> None:
    """Representative per-individual feature output satisfies its schema."""
    payload = {
        "schema_version": foo.SCHEMA_FEATURES,
        "generated_at": "2026-06-02T00:00:00",
        "task": "T1.33 per-individual local PH features",
        "params": {
            "k_grid": [10, 20, 50],
            "k_primary": 20,
            "seed": 42,
            "n_individuals": 2,
            "landscape_n_points": 256,
            "distance_metric": "euclidean",
            "filtration": "vietoris-rips",
            "max_dim": 1,
            "input_embeddings_path": "raw_bigram_embedding.npy",
            "input_foo_clusters_path": "foo_clusters.csv",
            "embedding_dim": 90,
        },
        "features_per_k": {
            f"k_{k}": [
                {"individual_id": 1, "max_h0_persistence": 0.0, "total_h1_persistence": 0.0, "landscape_integral_k1": 0.0},
                {"individual_id": 2, "max_h0_persistence": 1.0, "total_h1_persistence": 0.5, "landscape_integral_k1": 0.1},
            ]
            for k in [10, 20, 50]
        },
        "input_provenance": {
            "embeddings_sha256": "a" * 64,
            "foo_clusters_sha256": "b" * 64,
            "embeddings_shape": [2, 90],
        },
    }
    _assert_per_individual_features_contract(payload)
    bad = json.loads(json.dumps(payload))
    bad["params"]["k_grid"] = [20]
    with pytest.raises(AssertionError):
        _assert_per_individual_features_contract(bad)


def test_sibling_pair_permutation_json_schema() -> None:
    """Representative sibling-pair permutation output satisfies its schema."""
    samples = [0.2, 0.3, 0.4] + [0.5] * 4997
    payload = {
        "schema_version": foo.SCHEMA_SIBLING,
        "generated_at": "2026-06-02T00:00:00",
        "task": "T1.33 sibling-pair permutation test",
        "pre_registration": "2026-05-25",
        "params": {
            "B": 5000,
            "seed": 42,
            "icc_bootstrap_B": 1000,
            "k_primary": 20,
            "n_clusters_observed": 3,
            "n_individuals": 6,
            "pvalue_formula": "(r+1)/(B+1)",
            "pvalue_null_draws": 5000,
            "null_type": "constrained-shuffle",
            "distance_in_feature_space": "euclidean",
        },
        "observed": {"mean_within_pair_distance": 0.35, "n_sibling_pairs": 3},
        "null_distribution": {
            "mean_within_pair_distance_samples": samples,
            "mean": float(np.mean(samples)),
            "std": float(np.std(samples, ddof=1)),
            "min": min(samples),
            "max": max(samples),
        },
        "permutation_pvalue": (2 + 1) / (5000 + 1),
        "effect_size_ratio": 0.7,
        "per_feature_icc": {
            name: {
                "point_estimate": 0.1,
                "bootstrap_ci_lower": 0.0,
                "bootstrap_ci_upper": 0.2,
                "bootstrap_B": 1000,
            }
            for name in foo.FEATURE_NAMES
        },
        "input_provenance": {
            "per_individual_features_path": "features.json",
            "per_individual_features_sha256": "a" * 64,
            "foo_clusters_path": "foo.csv",
            "foo_clusters_sha256": "b" * 64,
        },
    }
    _assert_sibling_contract(payload)
    bad = json.loads(json.dumps(payload))
    bad["bootstrap_pvalue"] = 0.1
    with pytest.raises(AssertionError):
        _assert_sibling_contract(bad)


@pytest.mark.integration
def test_foo_topology_output_jsons_validate_against_schemas() -> None:
    """Validate every on-disk T1.33 JSON, if any exist."""
    ov = _load_contract("foo-topology-schemas/foo-topology-output-json-validation.yaml")["output_validation"]
    dispatch = {entry["filename_pattern"]: entry["schema_contract"] for entry in ov["file_dispatch"]}
    # The applies_to_glob is rooted under results/; only scan results/ and
    # outputs/ (per the coding guidelines) rather than the whole repository.
    for search_dir in (REPO_ROOT / "results", REPO_ROOT / "outputs"):
        if not search_dir.is_dir():
            continue
        for path in search_dir.rglob("*.json"):
            rel = path.relative_to(REPO_ROOT)
            if not rel.full_match(ov["applies_to_glob"]):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            schema_id = None
            for pattern, candidate in dispatch.items():
                if Path(path.name).match(pattern):
                    schema_id = candidate
                    break
            assert schema_id is not None, f"No schema dispatch matched {rel}"
            if schema_id == "per-individual-local-features-output":
                _assert_per_individual_features_contract(data)
            elif schema_id == "sibling-pair-permutation-output":
                _assert_sibling_contract(data)
            elif schema_id == "topology-distinctiveness-comparison-output":
                _assert_comparison_contract(data)
            else:
                raise AssertionError(f"Unexpected schema id {schema_id}")


def test_comparator_feature_definitions_construction() -> None:
    """C1/C2 feature construction and shared sibling machinery are correct."""
    trajectories = [
        ["EL", "EM", "EM", "EH"],
        ["EL", "EL", "EM", "EH"],
        ["IH", "IM", "IL", "IL"],
    ]
    c1, _ = ngram_embed(
        trajectories,
        include_bigrams=True,
        include_trigrams=False,
        tfidf=False,
        pca_dim=None,
        umap_dim=None,
        standardize=False,
    )
    c2 = foo.build_summary_trajectory_features(trajectories)
    assert c1.shape == (3, 90)
    assert c2.shape == (3, 10)
    np.testing.assert_allclose(c2[:, :9].sum(axis=1), 1.0)
    assert c2[0, 9] == 2.0
    assert c2[2, 9] == 2.0

    toy_features = np.array([[0.0], [2.0], [10.0], [14.0]], dtype=np.float64)
    toy_clusters = np.array([1, 1, 2, 2], dtype=np.int64)
    observed, n_pairs = foo.mean_within_pair_distance(toy_features, toy_clusters)
    assert n_pairs == 2
    assert observed == pytest.approx((2.0 + 4.0) / 2.0)

    analysis = foo.run_sibling_analysis(
        toy_features,
        toy_clusters,
        ["x"],
        B=10,
        seed=42,
        icc_bootstrap_B=10,
    )
    assert analysis.n_sibling_pairs == 2
    assert set(analysis.per_feature_icc) == {"x"}


def test_topology_distinctiveness_comparison_json_schema() -> None:
    """Representative comparison output satisfies its schema and verdict rule."""
    payload = {
        "schema_version": foo.SCHEMA_COMPARISON,
        "generated_at": "2026-06-02T00:00:00",
        "task": "T1.33 topology-distinctiveness comparison",
        "pre_registration": "2026-05-25",
        "params": {
            "B": 5000,
            "seed": 42,
            "icc_bootstrap_B": 1000,
            "k_primary": 20,
            "n_individuals": 6,
            "pvalue_formula": "(r+1)/(B+1)",
            "null_type": "constrained-shuffle",
            "distance_in_feature_space": "euclidean",
        },
        "arms": {
            "topological": {
                "feature_dim": 3,
                "permutation_pvalue": 0.01,
                "effect_size_ratio": 0.7,
                "n_icc_features": 3,
                "n_icc_ci_above_zero": 1,
                "max_icc": 0.2,
                "mean_icc": 0.1,
                "rejects": True,
            },
            "c1_bigram_coordinate": {
                "feature_dim": 90,
                "permutation_pvalue": 0.2,
                "effect_size_ratio": 0.95,
                "n_icc_features": 90,
                "n_icc_ci_above_zero": 0,
                "max_icc": 0.1,
                "mean_icc": 0.01,
                "rejects": False,
            },
            "c2_summary_trajectory": {
                "feature_dim": 10,
                "permutation_pvalue": 0.01,
                "effect_size_ratio": 0.9,
                "n_icc_features": 10,
                "n_icc_ci_above_zero": 1,
                "max_icc": 0.2,
                "mean_icc": 0.02,
                "rejects": True,
            },
        },
        "distinctiveness_verdict": "TOPOLOGY_DISTINCTIVE",
        "input_provenance": {
            "sibling_pair_permutation_path": "sibling.json",
            "sibling_pair_permutation_sha256": "a" * 64,
            "foo_clusters_path": "foo.csv",
            "foo_clusters_sha256": "b" * 64,
        },
    }
    _assert_comparison_contract(payload)
    bad = json.loads(json.dumps(payload))
    bad["distinctiveness_verdict"] = "NO_FOO_SIGNAL"
    with pytest.raises(AssertionError):
        _assert_comparison_contract(bad)
