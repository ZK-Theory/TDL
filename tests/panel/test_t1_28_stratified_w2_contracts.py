# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Binding tests for the T1.28 per-subgroup stratified W2 recompute
#   + per-family BH FDR contracts. Three contracts: recompute-output schema,
#   fdr-families-output schema, and the dispatch-routing output_validation.
"""Binding tests for T1.28 stratified W2 recompute and per-family FDR contracts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"


def _load_contract(rel_path: str) -> dict:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Conforming payload builders
# ─────────────────────────────────────────────────────────────────────────────


def _conforming_subgroup(
    stratifier: str = "gender",
    subgroup_id: str = "Female",
    n: int = 14402,
    actual_landmarks: int | None = None,
    t_ratio: float = 1.35,
    bca_ci: tuple[float, float] = (1.10, 1.62),
    w2_p: float = 0.001,
    landscape_l2_p: float = 0.002,
) -> dict:
    lm = min(5000, n) if actual_landmarks is None else actual_landmarks
    return {
        "stratifier": stratifier,
        "subgroup_id": subgroup_id,
        "n": n,
        "actual_landmarks": lm,
        "t_ratio": t_ratio,
        "bca_ci": list(bca_ci),
        "w2_p": w2_p,
        "w2_rejects": w2_p < 0.05,
        "landscape_l2_p": landscape_l2_p,
    }


def _conforming_dataset_block() -> dict:
    """Conforming USoc dataset block: gender(2)+nssec(3)+cohort(7) = 12 subgroups."""
    return {
        "subgroups": [
            _conforming_subgroup("gender", "Female", n=14402),
            _conforming_subgroup("gender", "Male", n=11243),
            _conforming_subgroup("nssec", "Intermediate", n=8000),
            _conforming_subgroup("nssec", "Professional/Managerial", n=9000),
            _conforming_subgroup("nssec", "Routine/Manual", n=7000),
            _conforming_subgroup("cohort", "1930s", n=900, actual_landmarks=900),
            _conforming_subgroup("cohort", "1940s", n=2500),
            _conforming_subgroup("cohort", "1950s", n=3800),
            _conforming_subgroup("cohort", "1960s", n=5200),
            _conforming_subgroup("cohort", "1970s", n=5100),
            _conforming_subgroup("cohort", "1980s", n=4900),
            _conforming_subgroup("cohort", "1990s", n=2100),
        ],
        "gender_n": 2,
        "nssec_n": 3,
        "cohort_n": 7,
    }


def _conforming_bhps_dataset_block() -> dict:
    """Conforming BHPS dataset block: gender(2)+nssec(3)+cohort(6) = 11 subgroups.

    BHPS has no 1990s respondents (panel ended 2009); 2026-06-28 amendment.
    """
    return {
        "subgroups": [
            _conforming_subgroup("gender", "Female", n=4200),
            _conforming_subgroup("gender", "Male", n=4309),
            _conforming_subgroup("nssec", "Intermediate", n=2100),
            _conforming_subgroup("nssec", "Professional/Managerial", n=1800),
            _conforming_subgroup("nssec", "Routine/Manual", n=2500),
            _conforming_subgroup("cohort", "1930s", n=986, actual_landmarks=986),
            _conforming_subgroup("cohort", "1940s", n=1360),
            _conforming_subgroup("cohort", "1950s", n=1373),
            _conforming_subgroup("cohort", "1960s", n=1722),
            _conforming_subgroup("cohort", "1970s", n=1064),
            _conforming_subgroup("cohort", "1980s", n=223, actual_landmarks=223),
        ],
        "gender_n": 2,
        "nssec_n": 3,
        "cohort_n": 6,
    }


def _conforming_recompute_payload() -> dict:
    return {
        "schema_version": "stratified-w2-recompute-v1",
        "generated_at": "2026-06-28",
        "task": "T1.28 per-subgroup stratified W2 recompute + per-family FDR",
        "pre_registration": (
            "results/panel_methodology/fdr/pre_registrations_2026-06-13.json"
        ),
        "inputs": {
            "git_head": "abc123def",
            "frozen_loadings_provenance": {
                "usoc": "results/trajectory_tda_integration/embeddings.npy",
                "bhps": "results/trajectory_tda_bhps/embeddings.npy",
            },
        },
        "params": {
            "null_model": "markov-1",
            "frozen_loadings": True,
            "B": 1000,
            "seed": 42,
            "p_value_formula": "(r+1)/(B+1)",
            "alpha": 0.05,
        },
        "datasets": {
            "usoc": _conforming_dataset_block(),
            "bhps": _conforming_bhps_dataset_block(),
        },
    }


def _conforming_fdr_tests(subgroup_ids: list[str]) -> list[dict]:
    """Build conforming per-test records with retained effect sizes."""
    tests = []
    for sid in subgroup_ids:
        raw_p = 0.01
        adj_p = 0.025  # adjusted_p >= raw_p
        tests.append(
            {
                "subgroup_id": sid,
                "raw_p": raw_p,
                "adjusted_p": adj_p,
                "rejected": adj_p < 0.05,
                "t_ratio": 1.35,
                "bca_ci": [1.10, 1.62],
            }
        )
    return tests


def _conforming_fdr_dataset_block() -> dict:
    """Conforming USoc FDR block: gender(2)+nssec(3)+cohort(7)."""
    return {
        "families": {
            "gender": {
                "method": "BH",
                "n_tests": 2,
                "tests": _conforming_fdr_tests(["Female", "Male"]),
            },
            "nssec": {
                "method": "BH",
                "n_tests": 3,
                "tests": _conforming_fdr_tests(
                    ["Intermediate", "Professional/Managerial", "Routine/Manual"]
                ),
            },
            "cohort": {
                "method": "BH",
                "n_tests": 7,
                "tests": _conforming_fdr_tests(
                    ["1930s", "1940s", "1950s", "1960s", "1970s", "1980s", "1990s"]
                ),
            },
        }
    }


def _conforming_fdr_bhps_dataset_block() -> dict:
    """Conforming BHPS FDR block: gender(2)+nssec(3)+cohort(6). No 1990s."""
    return {
        "families": {
            "gender": {
                "method": "BH",
                "n_tests": 2,
                "tests": _conforming_fdr_tests(["Female", "Male"]),
            },
            "nssec": {
                "method": "BH",
                "n_tests": 3,
                "tests": _conforming_fdr_tests(
                    ["Intermediate", "Professional/Managerial", "Routine/Manual"]
                ),
            },
            "cohort": {
                "method": "BH",
                "n_tests": 6,
                "tests": _conforming_fdr_tests(
                    ["1930s", "1940s", "1950s", "1960s", "1970s", "1980s"]
                ),
            },
        }
    }


def _conforming_fdr_payload() -> dict:
    return {
        "schema_version": "stratified-w2-fdr-families-v1",
        "generated_at": "2026-06-28",
        "pre_registration": (
            "results/panel_methodology/fdr/pre_registrations_2026-06-13.json"
            " + 2026-06-27 amendment"
        ),
        "datasets": {
            "usoc": _conforming_fdr_dataset_block(),
            "bhps": _conforming_fdr_bhps_dataset_block(),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Validators (raise AssertionError on invalid payloads)
# ─────────────────────────────────────────────────────────────────────────────


def _validate_recompute_payload(payload: dict) -> None:  # noqa: C901
    """Validate a T1.28 recompute payload; raise AssertionError if invalid."""
    assert payload.get("schema_version") == "stratified-w2-recompute-v1", (
        "schema_version must be 'stratified-w2-recompute-v1', "
        f"got {payload.get('schema_version')!r}"
    )

    params = payload.get("params", {})
    assert params.get("frozen_loadings") is True, (
        "params.frozen_loadings must be True"
    )
    assert isinstance(params.get("B"), int) and params["B"] >= 1000, (
        f"params.B must be int >= 1000, got {params.get('B')!r}"
    )
    assert params.get("seed") == 42, (
        f"params.seed must be 42, got {params.get('seed')!r}"
    )
    assert params.get("null_model") == "markov-1", (
        f"params.null_model must be 'markov-1', got {params.get('null_model')!r}"
    )
    assert params.get("p_value_formula") == "(r+1)/(B+1)", (
        f"params.p_value_formula must be '(r+1)/(B+1)', "
        f"got {params.get('p_value_formula')!r}"
    )

    datasets = payload.get("datasets", {})
    assert set(datasets.keys()) == {"usoc", "bhps"}, (
        f"datasets must contain exactly usoc and bhps, got {set(datasets.keys())}"
    )

    # Per-dataset expected counts (2026-06-28 amendment: BHPS has no 1990s cohort)
    _expected_cohort_n = {"usoc": 7, "bhps": 6}
    _expected_total = {"usoc": 12, "bhps": 11}

    for ds_name, ds in datasets.items():
        exp_cohort_n = _expected_cohort_n[ds_name]
        exp_total = _expected_total[ds_name]

        assert ds.get("gender_n") == 2, (
            f"{ds_name}.gender_n must be 2, got {ds.get('gender_n')!r}"
        )
        assert ds.get("nssec_n") == 3, (
            f"{ds_name}.nssec_n must be 3, got {ds.get('nssec_n')!r}"
        )
        assert ds.get("cohort_n") == exp_cohort_n, (
            f"{ds_name}.cohort_n must be {exp_cohort_n}, got {ds.get('cohort_n')!r}"
        )

        subgroups = ds.get("subgroups", [])
        assert len(subgroups) == exp_total, (
            f"{ds_name} must have {exp_total} subgroups, got {len(subgroups)}"
        )

        for sg in subgroups:
            sg_id = sg.get("subgroup_id", "?")
            assert sg.get("stratifier") in {"gender", "nssec", "cohort"}, (
                f"{ds_name}/{sg_id}: stratifier must be gender/nssec/cohort, "
                f"got {sg.get('stratifier')!r}"
            )
            n = sg.get("n")
            assert isinstance(n, int) and n > 0, (
                f"{ds_name}/{sg_id}: n must be int > 0, got {n!r}"
            )
            lm = sg.get("actual_landmarks")
            assert isinstance(lm, int) and lm > 0 and lm <= min(5000, n), (
                f"{ds_name}/{sg_id}: actual_landmarks must be int > 0 and "
                f"<= min(5000, n={n}), got {lm!r}"
            )
            t_r = sg.get("t_ratio")
            assert isinstance(t_r, (int, float)) and t_r == t_r, (
                f"{ds_name}/{sg_id}: t_ratio must be finite float, got {t_r!r}"
            )
            bca = sg.get("bca_ci")
            assert isinstance(bca, list) and len(bca) == 2, (
                f"{ds_name}/{sg_id}: bca_ci must be [lo, hi], got {bca!r}"
            )
            lo, hi = bca
            assert (
                isinstance(lo, (int, float))
                and isinstance(hi, (int, float))
                and lo == lo  # finite (NaN != NaN)
                and hi == hi
                and lo <= hi
            ), (
                f"{ds_name}/{sg_id}: bca_ci must be ordered finite floats, "
                f"got [{lo}, {hi}]"
            )
            w2_p = sg.get("w2_p")
            assert isinstance(w2_p, (int, float)) and 0.0 <= w2_p <= 1.0, (
                f"{ds_name}/{sg_id}: w2_p must be float in [0,1], got {w2_p!r}"
            )
            w2_rejects = sg.get("w2_rejects")
            assert w2_rejects == (w2_p < 0.05), (
                f"{ds_name}/{sg_id}: w2_rejects must equal (w2_p < 0.05), "
                f"got w2_rejects={w2_rejects}, w2_p={w2_p}"
            )
            l2_p = sg.get("landscape_l2_p")
            assert isinstance(l2_p, (int, float)) and 0.0 <= l2_p <= 1.0, (
                f"{ds_name}/{sg_id}: landscape_l2_p must be float in [0,1], "
                f"got {l2_p!r}"
            )

    for forbidden in ("per_call_pca", "pairwise_wasserstein"):
        assert forbidden not in payload, (
            f"forbidden key '{forbidden}' present in payload"
        )


def _validate_fdr_payload(payload: dict) -> None:
    """Validate a T1.28 per-family FDR payload; raise AssertionError if invalid."""
    assert payload.get("schema_version") == "stratified-w2-fdr-families-v1", (
        "schema_version must be 'stratified-w2-fdr-families-v1', "
        f"got {payload.get('schema_version')!r}"
    )

    datasets = payload.get("datasets", {})
    assert set(datasets.keys()) == {"usoc", "bhps"}, (
        f"datasets must contain exactly usoc and bhps, got {set(datasets.keys())}"
    )

    # Per-dataset cohort n_tests (2026-06-28 amendment: BHPS has no 1990s cohort)
    _cohort_n_tests = {"usoc": 7, "bhps": 6}

    for ds_name, ds in datasets.items():
        expected: dict[str, tuple[str, int]] = {
            "gender": ("BH", 2),
            "nssec": ("BH", 3),
            "cohort": ("BH", _cohort_n_tests[ds_name]),
        }

        families = ds.get("families", {})
        assert set(families.keys()) == set(expected), (
            f"{ds_name}.families must have exactly gender/nssec/cohort, "
            f"got {set(families.keys())}"
        )

        for fam_name, (exp_method, exp_n) in expected.items():
            fam = families[fam_name]
            assert fam.get("method") == exp_method, (
                f"{ds_name}.families.{fam_name}.method must be '{exp_method}', "
                f"got {fam.get('method')!r}"
            )
            assert fam.get("n_tests") == exp_n, (
                f"{ds_name}.families.{fam_name}.n_tests must be {exp_n}, "
                f"got {fam.get('n_tests')!r}"
            )

            for t in fam.get("tests", []):
                t_id = t.get("subgroup_id", "?")
                raw_p = t.get("raw_p")
                adj_p = t.get("adjusted_p")
                assert isinstance(raw_p, (int, float)) and 0.0 <= raw_p <= 1.0, (
                    f"{ds_name}.{fam_name}/{t_id}: raw_p must be in [0,1], "
                    f"got {raw_p!r}"
                )
                assert isinstance(adj_p, (int, float)) and 0.0 <= adj_p <= 1.0, (
                    f"{ds_name}.{fam_name}/{t_id}: adjusted_p must be in [0,1], "
                    f"got {adj_p!r}"
                )
                assert adj_p >= raw_p, (
                    f"{ds_name}.{fam_name}/{t_id}: adjusted_p ({adj_p}) must "
                    f">= raw_p ({raw_p})"
                )
                assert "t_ratio" in t, (
                    f"{ds_name}.{fam_name}/{t_id}: effect size t_ratio missing"
                )
                bca = t.get("bca_ci")
                assert (
                    isinstance(bca, list)
                    and len(bca) == 2
                    and bca[0] == bca[0]
                    and bca[1] == bca[1]
                    and bca[0] <= bca[1]
                ), (
                    f"{ds_name}.{fam_name}/{t_id}: bca_ci must be ordered "
                    f"finite [lo, hi], got {bca!r}"
                )

    for forbidden in ("pooled_single_family", "bonferroni"):
        assert forbidden not in payload, (
            f"forbidden key '{forbidden}' present in payload"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Contract binding tests
# ─────────────────────────────────────────────────────────────────────────────


def test_stratified_w2_recompute_output_schema() -> None:
    """Accepts conforming recompute payload; rejects each must_assert violation."""
    conforming = _conforming_recompute_payload()

    # contract is loadable
    contract = _load_contract("panel-output-schemas/stratified-w2-recompute-output.yaml")
    assert contract["id"] == "stratified-w2-recompute-output"

    # (a) conforming payload accepted
    _validate_recompute_payload(conforming)

    # (b) wrong schema_version
    bad = copy.deepcopy(conforming)
    bad["schema_version"] = "legacy-stratified-v0"
    with pytest.raises(AssertionError, match="schema_version"):
        _validate_recompute_payload(bad)

    # (b) frozen_loadings not true
    bad = copy.deepcopy(conforming)
    bad["params"]["frozen_loadings"] = False
    with pytest.raises(AssertionError, match="frozen_loadings"):
        _validate_recompute_payload(bad)

    # (b) B < 1000
    bad = copy.deepcopy(conforming)
    bad["params"]["B"] = 100
    with pytest.raises(AssertionError, match="B must be int >= 1000"):
        _validate_recompute_payload(bad)

    # (b) seed != 42
    bad = copy.deepcopy(conforming)
    bad["params"]["seed"] = 0
    with pytest.raises(AssertionError, match="seed must be 42"):
        _validate_recompute_payload(bad)

    # (b) wrong null_model
    bad = copy.deepcopy(conforming)
    bad["params"]["null_model"] = "markov-2"
    with pytest.raises(AssertionError, match="null_model"):
        _validate_recompute_payload(bad)

    # (b) wrong p_value_formula
    bad = copy.deepcopy(conforming)
    bad["params"]["p_value_formula"] = "r/B"
    with pytest.raises(AssertionError, match="p_value_formula"):
        _validate_recompute_payload(bad)

    # (c) datasets missing bhps
    bad = copy.deepcopy(conforming)
    del bad["datasets"]["bhps"]
    with pytest.raises(AssertionError, match="usoc and bhps"):
        _validate_recompute_payload(bad)

    # (d) nssec_n = 6 (old pairwise count — must be rejected)
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["nssec_n"] = 6
    with pytest.raises(AssertionError, match="nssec_n must be 3"):
        _validate_recompute_payload(bad)

    # (d) cohort_n = 42 on usoc (old pairwise count — must be rejected)
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["cohort_n"] = 42
    with pytest.raises(AssertionError, match="cohort_n must be 7"):
        _validate_recompute_payload(bad)

    # (d) usoc cohort_n = 6 (wrong — USoc expects 7, not BHPS's 6)
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["cohort_n"] = 6
    with pytest.raises(AssertionError, match="cohort_n must be 7"):
        _validate_recompute_payload(bad)

    # (d) bhps cohort_n = 7 (wrong — BHPS expects 6; no 1990s respondents)
    bad = copy.deepcopy(conforming)
    bad["datasets"]["bhps"]["cohort_n"] = 7
    # Also add a 12th subgroup so total==12 to test cohort_n check, not total check
    bad["datasets"]["bhps"]["subgroups"].append(
        _conforming_subgroup("cohort", "1990s", n=50, actual_landmarks=50)
    )
    with pytest.raises(AssertionError, match="cohort_n must be 6"):
        _validate_recompute_payload(bad)

    # (d) bhps total subgroups = 12 instead of 11 (cohort_n is 6 but subgroups list is 12)
    bad = copy.deepcopy(conforming)
    bad["datasets"]["bhps"]["subgroups"].append(
        _conforming_subgroup("cohort", "extra", n=50, actual_landmarks=50)
    )
    with pytest.raises(AssertionError, match="must have 11 subgroups"):
        _validate_recompute_payload(bad)

    # (e) w2_rejects disagrees with w2_p < 0.05
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["subgroups"][0]["w2_p"] = 0.9
    bad["datasets"]["usoc"]["subgroups"][0]["w2_rejects"] = True
    with pytest.raises(AssertionError, match="w2_rejects"):
        _validate_recompute_payload(bad)

    # (f) bca_ci unordered (lo > hi)
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["subgroups"][0]["bca_ci"] = [1.62, 1.10]
    with pytest.raises(AssertionError, match="bca_ci"):
        _validate_recompute_payload(bad)

    # (f) w2_p outside [0,1]
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["subgroups"][0]["w2_p"] = 1.5
    with pytest.raises(AssertionError, match="w2_p must be float in"):
        _validate_recompute_payload(bad)

    # (g) actual_landmarks > min(5000, n) — exceeds cap
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["subgroups"][0]["actual_landmarks"] = 6000
    with pytest.raises(AssertionError, match="actual_landmarks"):
        _validate_recompute_payload(bad)

    # (g) actual_landmarks exceeds n for a small subgroup
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["subgroups"][5]["n"] = 800
    bad["datasets"]["usoc"]["subgroups"][5]["actual_landmarks"] = 900
    with pytest.raises(AssertionError, match="actual_landmarks"):
        _validate_recompute_payload(bad)

    # (h) per_call_pca present — frozen-loadings violation
    bad = copy.deepcopy(conforming)
    bad["per_call_pca"] = True
    with pytest.raises(AssertionError, match="per_call_pca"):
        _validate_recompute_payload(bad)

    # (h) pairwise_wasserstein present — retired legacy construction
    bad = copy.deepcopy(conforming)
    bad["pairwise_wasserstein"] = {"(Female, Male, H0)": 33.7}
    with pytest.raises(AssertionError, match="pairwise_wasserstein"):
        _validate_recompute_payload(bad)


def test_stratified_w2_fdr_families_output_schema() -> None:
    """Accepts conforming FDR payload; rejects each must_assert violation."""
    conforming = _conforming_fdr_payload()

    contract = _load_contract("panel-output-schemas/stratified-w2-fdr-families-output.yaml")
    assert contract["id"] == "stratified-w2-fdr-families-output"

    # (a) conforming payload accepted
    _validate_fdr_payload(conforming)

    # (a) wrong schema_version
    bad = copy.deepcopy(conforming)
    bad["schema_version"] = "stratified-w2-v0"
    with pytest.raises(AssertionError, match="schema_version"):
        _validate_fdr_payload(bad)

    # (b) datasets missing bhps
    bad = copy.deepcopy(conforming)
    del bad["datasets"]["bhps"]
    with pytest.raises(AssertionError, match="usoc and bhps"):
        _validate_fdr_payload(bad)

    # (c) families missing cohort
    bad = copy.deepcopy(conforming)
    del bad["datasets"]["usoc"]["families"]["cohort"]
    with pytest.raises(AssertionError, match="gender/nssec/cohort"):
        _validate_fdr_payload(bad)

    # (d) cohort.method != 'BH' — old BY was for pairwise model, not per-subgroup
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["families"]["cohort"]["method"] = "BY"
    with pytest.raises(AssertionError, match="method must be 'BH'"):
        _validate_fdr_payload(bad)

    # (d) gender.method wrong
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["families"]["gender"]["method"] = "bonferroni"
    with pytest.raises(AssertionError, match="method must be 'BH'"):
        _validate_fdr_payload(bad)

    # (e) family n_tests wrong — nssec n_tests = 6 (old pairwise count)
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["families"]["nssec"]["n_tests"] = 6
    with pytest.raises(AssertionError, match="n_tests must be 3"):
        _validate_fdr_payload(bad)

    # (e) cohort n_tests = 42 on usoc (old pairwise count)
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["families"]["cohort"]["n_tests"] = 42
    with pytest.raises(AssertionError, match="n_tests must be 7"):
        _validate_fdr_payload(bad)

    # (e) usoc cohort n_tests = 6 (wrong — USoc expects 7)
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["families"]["cohort"]["n_tests"] = 6
    with pytest.raises(AssertionError, match="n_tests must be 7"):
        _validate_fdr_payload(bad)

    # (e) bhps cohort n_tests = 7 (wrong — BHPS expects 6; no 1990s)
    bad = copy.deepcopy(conforming)
    bad["datasets"]["bhps"]["families"]["cohort"]["n_tests"] = 7
    with pytest.raises(AssertionError, match="n_tests must be 6"):
        _validate_fdr_payload(bad)

    # (f) adjusted_p < raw_p
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["families"]["gender"]["tests"][0]["raw_p"] = 0.04
    bad["datasets"]["usoc"]["families"]["gender"]["tests"][0]["adjusted_p"] = 0.01
    with pytest.raises(AssertionError, match="adjusted_p"):
        _validate_fdr_payload(bad)

    # (f) adjusted_p outside [0,1]
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["families"]["gender"]["tests"][0]["adjusted_p"] = 1.5
    with pytest.raises(AssertionError, match="adjusted_p must be in"):
        _validate_fdr_payload(bad)

    # (g) effect size t_ratio dropped
    bad = copy.deepcopy(conforming)
    del bad["datasets"]["usoc"]["families"]["nssec"]["tests"][0]["t_ratio"]
    with pytest.raises(AssertionError, match="t_ratio missing"):
        _validate_fdr_payload(bad)

    # (g) bca_ci unordered
    bad = copy.deepcopy(conforming)
    bad["datasets"]["usoc"]["families"]["nssec"]["tests"][0]["bca_ci"] = [1.62, 1.10]
    with pytest.raises(AssertionError, match="bca_ci"):
        _validate_fdr_payload(bad)

    # (h) pooled_single_family present
    bad = copy.deepcopy(conforming)
    bad["pooled_single_family"] = True
    with pytest.raises(AssertionError, match="pooled_single_family"):
        _validate_fdr_payload(bad)

    # (h) bonferroni present
    bad = copy.deepcopy(conforming)
    bad["bonferroni"] = True
    with pytest.raises(AssertionError, match="bonferroni"):
        _validate_fdr_payload(bad)


def test_stratified_w2_fdr_json_validation_dispatch() -> None:
    """Dispatch routing: recompute→recompute-schema, bh_per_family→fdr-schema, legacy excluded."""
    contract = _load_contract(
        "panel-output-schemas/stratified-w2-fdr-output-json-validation.yaml"
    )
    assert contract["id"] == "stratified-w2-fdr-output-json-validation"

    ov = contract["output_validation"]
    file_dispatch = ov["file_dispatch"]
    dispatch_map = {
        entry["filename_pattern"]: entry["schema_contract"] for entry in file_dispatch
    }

    # (a) recompute file routes to the recompute schema
    assert dispatch_map.get("stratified_w2_recompute_*.json") == "stratified-w2-recompute-output", (
        f"recompute file should route to stratified-w2-recompute-output, got {dispatch_map}"
    )

    # (b) bh_per_family file routes to FDR-families schema
    assert dispatch_map.get("stratified_w2_bh_per_family_*.json") == "stratified-w2-fdr-families-output", (
        "bh_per_family file should route to stratified-w2-fdr-families-output"
    )

    # both referenced schemas are declared in schema_contracts
    schema_contracts = ov["schema_contracts"]
    assert "stratified-w2-recompute-output" in schema_contracts
    assert "stratified-w2-fdr-families-output" in schema_contracts

    # (c) legacy file does NOT match any dispatch pattern
    legacy_name = "06_stratified.json"
    for entry in file_dispatch:
        pat = entry["filename_pattern"]
        # Convert glob pattern to prefix check (pattern is prefix_*.json)
        prefix = pat.replace("_*.json", "_")
        assert not legacy_name.startswith(prefix), (
            f"Legacy '{legacy_name}' must not match dispatch pattern '{pat}'"
        )

    # (c) legacy file path does not match applies_to_glob
    glob_pattern = ov["applies_to_glob"]
    # glob is results/panel_methodology/fdr/stratified_w2_*.json;
    # legacy is results/trajectory_tda_integration/06_stratified.json — different dir
    legacy_path = Path("results/trajectory_tda_integration/06_stratified.json")
    assert not any(
        legacy_path.name.startswith(pat.replace("_*.json", "_"))
        for pat in [p["filename_pattern"] for p in file_dispatch]
    ), "Legacy 06_stratified.json must NOT be captured by stratified_w2_* dispatch patterns"

    # validate any on-disk output JSONs matching the glob pattern
    for json_path in REPO_ROOT.rglob("*.json"):
        rel = json_path.relative_to(REPO_ROOT)
        rel_str = str(rel).replace("\\", "/")
        # Only process files under results/panel_methodology/fdr/stratified_w2_*.json
        if not rel_str.startswith("results/panel_methodology/fdr/stratified_w2_"):
            continue
        name = json_path.name
        data = json.loads(json_path.read_text(encoding="utf-8"))
        if Path(name).match("stratified_w2_recompute_*.json"):
            _validate_recompute_payload(data)
        elif Path(name).match("stratified_w2_bh_per_family_*.json"):
            _validate_fdr_payload(data)
