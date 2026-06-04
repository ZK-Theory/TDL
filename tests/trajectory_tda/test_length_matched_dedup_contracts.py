# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Binding tests for the length-matched landmark dedup-via-n_perm
#   amendment (Pre-reg #5 redo, 2026-05-30). Pairs 1:1 with the four
#   contracts authored under that amendment:
#     - contracts/topology-invariants/length-matched-dedup-via-n-perm.yaml
#     - contracts/stage1-output-schemas/length-matched-run-params.yaml
#     - contracts/stage1-output-schemas/length-matched-run-params-validation.yaml
#     - contracts/topology-invariants/dedup-equivalence-canary.yaml
"""Binding tests for length-matched landmark dedup via ripser n_perm.

Three synthetic tests run in the default fast path (called by the pre-commit
hook). The canary regenerates the T1.2f truncate frozen observed L=5000
landmark sample from the BHPS checkpoint and is marked slow+integration; it
gates the T1.2g rerun per the 2026-05-30 vault [DECISION].
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import persim
import pytest
import ripser
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
DIAGNOSTICS_DIR = REPO_ROOT / ".apm" / "diagnostics"
TAU = 1e-10
# Per-dimension canary tolerances per the 2026-05-30 contract update:
# H1 is strict (paper claims operate here); H0 is relaxed to absorb the
# persim/ripser float32 precision floor (~1/2^25 = 2.98e-8) that surfaces
# when extra near-duplicate H0 features are matched to the diagonal.
TAU_CANARY_H0 = 1e-6
TAU_CANARY_H1 = 1e-10


def _load_contract(rel_path: str) -> dict:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# 1. Formula binding — length-matched-dedup-via-n-perm
# ---------------------------------------------------------------------------


def test_length_matched_dedup_via_n_perm_construction() -> None:
    """N is the smallest k with eps_k <= tau; PD(X[I])=PD(unique(X)) identity."""
    from poverty_tda.topology.multidim_ph import (
        DEDUP_TOLERANCE,
        compute_greedy_dedup_count,
    )

    assert DEDUP_TOLERANCE == 1e-10

    # (a) Replicated-row matrix: K distinct rows each repeated to total 100 rows.
    K = 10
    rng = np.random.default_rng(seed=20260530)
    distinct = rng.normal(scale=5.0, size=(K, 3))
    X = np.vstack([distinct, distinct, distinct, distinct, distinct,
                   distinct, distinct, distinct, distinct, distinct])
    assert X.shape == (100, 3)

    N, eps, indices = compute_greedy_dedup_count(X)
    # K distinct row classes; greedy from row 0 (a distinct row) selects
    # one new distinct row per step until all K classes are covered.
    assert K <= N <= K + 1, f"N={N} not in {{{K}, {K + 1}}}"
    assert eps <= TAU, f"eps_N={eps} > tau"
    assert indices.shape == (N,), f"index set shape {indices.shape} != ({N},)"
    assert indices.dtype == np.int64

    # (b) PD identity: PD(X[I]) = PD(unique(X)) — external indexing realises
    #     the duplicate-invariance of Rips PH directly. Both PDs computed
    #     via exact ripser (no n_perm shortcut), so this isolates the
    #     mathematical identity from any ripser-internal-greedy artefact.
    pd_dedup = ripser.ripser(X[indices], maxdim=1)["dgms"]
    pd_unique = ripser.ripser(distinct, maxdim=1)["dgms"]
    for dim in (0, 1):
        d = float(persim.bottleneck(pd_dedup[dim], pd_unique[dim]))
        assert d <= TAU, f"H{dim}: bottleneck {d} > {TAU}"

    # (c) All-distinct synthetic matrix: N == L, I is a permutation of
    #     {0,...,L-1}; scheme reduces to the exact-ripser path on a
    #     reordered X with no behavioural change.
    Y = rng.normal(scale=5.0, size=(50, 3))
    N_full, _, I_full = compute_greedy_dedup_count(Y)
    assert N_full == Y.shape[0], (
        f"all-distinct fallback expected N=={Y.shape[0]}, got {N_full}"
    )
    assert sorted(I_full.tolist()) == list(range(Y.shape[0])), (
        "fallback index set must be a permutation of all row indices"
    )

    # (d) Determinism: the greedy permutation starts from row index 0 with
    #     Euclidean distance, so the result is deterministic given the
    #     input ordering. Calling twice yields identical (N, eps, I).
    N_a, eps_a, I_a = compute_greedy_dedup_count(X)
    N_b, eps_b, I_b = compute_greedy_dedup_count(X)
    assert N_a == N_b and eps_a == eps_b
    assert np.array_equal(I_a, I_b)

    with pytest.raises(AssertionError):
        assert N < K or N > K + 1
    with pytest.raises(AssertionError):
        assert float(persim.bottleneck(pd_dedup[1], pd_unique[1])) > TAU
    with pytest.raises(AssertionError):
        assert N_full != Y.shape[0]
    with pytest.raises(AssertionError):
        assert not np.array_equal(I_a, I_b)


# ---------------------------------------------------------------------------
# 2. Schema binding — length-matched-run-params
# ---------------------------------------------------------------------------


def _valid_run_params() -> dict:
    """Reference run_params dict that satisfies every contract constraint."""
    return {
        "L": 5000,
        "B": 1000,
        "seed": 42,
        "null_model": "markov-1",
        "frozen_loadings": True,
        "strategy": "truncate",
        "target_years": 13,
        "pvalue_formula": "(r+1)/(B+1)",
        "n_perm_used_observed": 5000,
        "covering_radius_at_n_perm_observed": 0.0,
        "n_perm_used_null_summary": {
            "min": 5000,
            "median": 5000,
            "max": 5000,
            "all_equal_to_L": True,
        },
        "covering_radius_at_n_perm_null_summary": {
            "min": 0.0,
            "median": 0.0,
            "max": 0.0,
            "max_observed": 0.0,
        },
        "dedup_tolerance": 1e-10,
        "dedup_strategy": "greedy-permutation-external-indexing",
    }


def _validate_run_params(rp: dict) -> list[str]:
    """Return contract violations for a run_params dict.

    Loads required and forbidden key names from the schema YAML so the
    binding test stays in sync; the value-level constraints in the schema
    description are encoded explicitly here.
    """
    schema = _load_contract("stage1-output-schemas/length-matched-run-params.yaml")
    required = [k["name"] for k in schema["schema_def"]["required_keys"]]
    forbidden = [k["name"] for k in schema["schema_def"].get("forbidden_keys", [])]

    errors: list[str] = []
    missing = [k for k in required if k not in rp]
    if missing:
        errors.extend(f"missing required key: {k}" for k in missing)
        return errors  # downstream value checks would error on KeyError

    for k in forbidden:
        if k in rp:
            errors.append(f"forbidden key '{k}' present")

    expected_types = {
        "L": int,
        "B": int,
        "seed": int,
        "null_model": str,
        "frozen_loadings": bool,
        "strategy": str,
        "target_years": int,
        "pvalue_formula": str,
        "n_perm_used_observed": int,
        "covering_radius_at_n_perm_observed": (int, float),
        "n_perm_used_null_summary": dict,
        "covering_radius_at_n_perm_null_summary": dict,
        "dedup_tolerance": (int, float),
        "dedup_strategy": str,
    }
    for key, expected_type in expected_types.items():
        if not isinstance(rp[key], expected_type):
            errors.append(f"{key} has wrong type {type(rp[key]).__name__}")
    if errors:
        return errors

    if rp["L"] != 5000:
        errors.append(f"L != 5000 (got {rp['L']})")
    if rp["frozen_loadings"] is not True:
        errors.append("frozen_loadings must be True")
    if rp["strategy"] not in {"truncate", "first13"}:
        errors.append(f"strategy {rp['strategy']!r} not in {{'truncate','first13'}}")
    if rp["target_years"] != 13:
        errors.append(f"target_years != 13 (got {rp['target_years']})")
    if rp["dedup_tolerance"] != 1e-10:
        errors.append(f"dedup_tolerance != 1e-10 (got {rp['dedup_tolerance']})")
    if rp["dedup_strategy"] != "greedy-permutation-external-indexing":
        errors.append(f"dedup_strategy mismatch (got {rp['dedup_strategy']!r})")
    if not str(rp["null_model"]).startswith("markov-"):
        errors.append(f"null_model must start with 'markov-' (got {rp['null_model']!r})")
    if rp["pvalue_formula"] != "(r+1)/(B+1)":
        errors.append(
            f"pvalue_formula must equal '(r+1)/(B+1)' (got {rp['pvalue_formula']!r})"
        )

    n_obs = rp["n_perm_used_observed"]
    cov_obs = rp["covering_radius_at_n_perm_observed"]
    L = rp["L"]
    if not (1 <= n_obs <= L):
        errors.append(f"n_perm_used_observed {n_obs} not in [1, {L}]")
    if n_obs < L and cov_obs > rp["dedup_tolerance"]:
        errors.append(
            f"n_perm_used_observed={n_obs} < L={L} but covering radius "
            f"{cov_obs} > dedup_tolerance — fallback that didn't fall back"
        )

    null_n = rp["n_perm_used_null_summary"]
    for key in ("min", "median", "max", "all_equal_to_L"):
        if key not in null_n:
            errors.append(f"n_perm_used_null_summary missing key: {key}")

    null_cov = rp["covering_radius_at_n_perm_null_summary"]
    for key in ("min", "median", "max", "max_observed"):
        if key not in null_cov:
            errors.append(f"covering_radius_at_n_perm_null_summary missing key: {key}")

    return errors


def _assert_valid_run_params(rp: dict) -> None:
    """Assert a length-matched run_params block carries the required dedup provenance fields."""
    errors = _validate_run_params(rp)
    assert not errors, "run_params schema violations: " + "; ".join(errors)


def test_length_matched_run_params_schema() -> None:
    """Valid run_params passes; each contract-listed violation rejects."""
    _assert_valid_run_params(_valid_run_params())

    # (a) L != 5000
    bad = _valid_run_params()
    bad["L"] = 2500
    with pytest.raises(AssertionError):
        _assert_valid_run_params(bad)

    # (b) frozen_loadings != True
    bad = _valid_run_params()
    bad["frozen_loadings"] = False
    with pytest.raises(AssertionError):
        _assert_valid_run_params(bad)

    # (c) strategy outside allowed set
    bad = _valid_run_params()
    bad["strategy"] = "midpoint"
    with pytest.raises(AssertionError):
        _assert_valid_run_params(bad)

    # (d) dedup_tolerance != 1e-10
    bad = _valid_run_params()
    bad["dedup_tolerance"] = 1e-8
    with pytest.raises(AssertionError):
        _assert_valid_run_params(bad)

    # (e) dedup_strategy != 'greedy-permutation-external-indexing'
    bad = _valid_run_params()
    bad["dedup_strategy"] = "ad-hoc-quotient"
    with pytest.raises(AssertionError):
        _assert_valid_run_params(bad)

    # (f) covering_radius_at_n_perm_observed > tolerance with n_obs < L
    bad = _valid_run_params()
    bad["n_perm_used_observed"] = 3000
    bad["covering_radius_at_n_perm_observed"] = 0.5
    with pytest.raises(AssertionError):
        _assert_valid_run_params(bad)

    # (g) presence of the forbidden singular 'n_perm' key
    bad = _valid_run_params()
    bad["n_perm"] = 5000
    with pytest.raises(AssertionError):
        _assert_valid_run_params(bad)


# ---------------------------------------------------------------------------
# 3. Output-validation binding — scan on-disk JSONs
# ---------------------------------------------------------------------------


def _matched_jsons(glob_pattern: str) -> list[Path]:
    matched: list[Path] = []
    for path in REPO_ROOT.rglob("*.json"):
        try:
            rel = path.relative_to(REPO_ROOT)
        except ValueError:
            continue
        if rel.full_match(glob_pattern):
            matched.append(path)
    return matched


def test_length_matched_run_params_jsons_validate_against_schema() -> None:
    """Validate every length-matched frozen JSON's run_params block.

    While the contract carries ``pending: true`` (the hook does not yet
    gate), this test records any violations to a diagnostic JSON but does
    not fail the suite — the existing 2026-05-29 T1.2f frozen file predates
    the amendment and is non-compliant by design. When the contract pending
    flag is cleared (after the dedup rerun produces compliant JSONs), this
    test gates and the assertion line below fires.
    """
    ov_contract = _load_contract(
        "stage1-output-schemas/length-matched-run-params-validation.yaml"
    )
    schema_pending = bool(_load_contract(
        "stage1-output-schemas/length-matched-run-params.yaml"
    ).get("pending", False))
    ov_pending = bool(ov_contract.get("pending", False))

    ov = ov_contract["output_validation"]
    glob_pattern = ov["applies_to_glob"]
    wrapper_key = ov["wrapper_key"]
    legacy_exempt = {Path(entry).as_posix() for entry in ov.get("legacy_exempt", [])}

    jsons = [
        path
        for path in _matched_jsons(glob_pattern)
        if path.relative_to(REPO_ROOT).as_posix() not in legacy_exempt
    ]
    failures: list[str] = []
    for path in jsons:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            failures.append(f"{path}: cannot load JSON: {e}")
            continue
        if not isinstance(data, dict) or wrapper_key not in data:
            failures.append(f"{path}: missing wrapper_key '{wrapper_key}'")
            continue
        rp = data[wrapper_key]
        if not isinstance(rp, dict):
            failures.append(f"{path}:{wrapper_key} is not a dict")
            continue
        for e in _validate_run_params(rp):
            failures.append(f"{path}: {e}")

    # While pending, record the diagnostic so the failures are queryable
    # from the artefact and do not block the suite.
    if schema_pending or ov_pending:
        DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
        (DIAGNOSTICS_DIR / "length-matched-run-params-validation-report.json").write_text(
            json.dumps(
                {
                    "schema_pending": schema_pending,
                    "ov_pending": ov_pending,
                    "scanned_files": [str(p.relative_to(REPO_ROOT)) for p in jsons],
                    "failures": failures,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return

    assert not failures, (
        "length-matched run_params schema violations:\n  " + "\n  ".join(failures)
    )


# ---------------------------------------------------------------------------
# 4. Canary binding — dedup-equivalence-canary
# ---------------------------------------------------------------------------


BHPS_CHECKPOINT = REPO_ROOT / "results" / "trajectory_tda_bhps"
CANARY_DIAG = DIAGNOSTICS_DIR / "dedup-equivalence-canary.json"


@pytest.mark.slow
@pytest.mark.integration
def test_dedup_equivalence_canary_on_t12f_truncate_landmarks() -> None:
    """Bottleneck d_B(PD_exact, PD_dedup) <= tau on T1.2f truncate landmarks.

    The default hook path validates the pinned canary diagnostic generated
    from the real T1.2f truncate frozen observed L=5000 landmark sample. Set
    REGENERATE_DEDUP_CANARY=1 to recompute the expensive direct-ripser canary
    and overwrite the diagnostic.
    """
    if os.environ.get("REGENERATE_DEDUP_CANARY") != "1":
        if not CANARY_DIAG.exists():
            pytest.fail(f"canary diagnostic missing: {CANARY_DIAG}")
        diagnostic = json.loads(CANARY_DIAG.read_text(encoding="utf-8"))
        assert diagnostic["spec"] == "dedup-equivalence-canary"
        assert diagnostic["strategy"] == "truncate"
        assert diagnostic["target_years"] == 13
        assert diagnostic["L"] == 5000
        assert diagnostic["n_perm_used"] == 4861
        assert diagnostic["passes_under_per_dimension_tolerance"] is True
        assert diagnostic["covering_radius_at_n_perm"] <= TAU
        distances = diagnostic["bottleneck_distances"]
        tolerances = diagnostic["per_dimension_tolerance"]
        assert distances["H0"] <= tolerances["H0"] == TAU_CANARY_H0
        assert distances["H1"] <= tolerances["H1"] == TAU_CANARY_H1
        assert diagnostic["third_run_under_external_indexing_direct_ripser"]["H1"] == 0.0
        return
    from poverty_tda.topology.multidim_ph import compute_greedy_dedup_count
    from trajectory_tda.embedding.ngram_embed import ngram_embed
    from trajectory_tda.scripts.stage1.run_bhps_length_matched import (
        apply_length_strategy,
        load_bhps_sequences,
    )
    from trajectory_tda.topology.permutation_nulls import maxmin_landmarks

    seq_path = BHPS_CHECKPOINT / "01_trajectories_sequences.json"
    if not seq_path.exists():
        pytest.fail(
            f"canary fixture missing: {seq_path} absent; "
            "test cannot regenerate truncate landmarks deterministically."
        )

    sequences, embed_kwargs = load_bhps_sequences(BHPS_CHECKPOINT)
    sub_seqs = apply_length_strategy(sequences, "truncate", 13)
    embeddings, _ = ngram_embed(sub_seqs, **embed_kwargs)
    _, landmarks = maxmin_landmarks(embeddings, 5000, seed=42)

    N_obs, eps_obs, I_obs = compute_greedy_dedup_count(landmarks)

    # Call ripser directly with no threshold so PD(X) and PD(X[I]) are both
    # the *complete* Rips filtration (no auto-threshold subsampling). The
    # compute_rips_ph wrapper auto-computes thresh from a 500-point random
    # subsample whose composition depends on |X|; passing X and X[I_obs]
    # through that wrapper produces *different* threshes and truncates H1
    # features near the cutoff differently, which is a confounder for this
    # canary. We isolate the dedup identity by removing the confounder.
    dgms_exact = ripser.ripser(landmarks, maxdim=1)["dgms"]
    dgms_dedup = ripser.ripser(landmarks[I_obs], maxdim=1)["dgms"]

    distances: dict[str, float] = {}
    for dim in (0, 1):
        d = float(persim.bottleneck(dgms_exact[dim], dgms_dedup[dim]))
        distances[f"H{dim}"] = d

    per_dim_tau = {"H0": TAU_CANARY_H0, "H1": TAU_CANARY_H1}

    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
    CANARY_DIAG.write_text(
        json.dumps(
            {
                "spec": "dedup-equivalence-canary",
                "strategy": "truncate",
                "target_years": 13,
                "L": int(landmarks.shape[0]),
                "n_perm_used": int(N_obs),
                "covering_radius_at_n_perm": float(eps_obs),
                "bottleneck_distances": distances,
                "per_dimension_tolerance": per_dim_tau,
                "tolerance_note": (
                    "H1 strict (1e-10) — paper claims operate on H1 loops; "
                    "H0 relaxed (1e-6) to absorb persim/ripser float32 floor "
                    "(~1/2^25 = 2.98e-8) from H0 diagonal-matching of extra "
                    "near-duplicate features. Operationally negligible "
                    "(H0 lifetimes are O(20+) in our data)."
                ),
                "ripser_version": ripser.__version__,
                "persim_version": persim.__version__,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    for dim_key, d in distances.items():
        tau_dim = per_dim_tau[dim_key]
        assert d <= tau_dim, (
            f"{dim_key}: bottleneck distance {d} exceeds tolerance {tau_dim}; "
            f"PD(exact) and PD(dedup via landmarks[I_obs], N={N_obs}) "
            f"diverge — length-matched-dedup-via-n-perm formula contract violated"
        )
