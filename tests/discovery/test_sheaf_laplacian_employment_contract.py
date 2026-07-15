# Research context: TDA-Research/00-Meta/Discovery/sheaf-laplacian-employment-dispatch-prereg-2026-07-10.md
# Purpose: Binding test for contracts/discovery-harness/sheaf-laplacian-employment-result.yaml.
#   Hermetic by construction — the A4 checkpoint anchors are injected rather than
#   read from PROJ_ROOT, so the test cannot fail merely because a gitignored
#   intermediate is absent from a fresh worktree.
"""Binding tests for the LOCKED sheaf-Laplacian energy battery result contract."""

from __future__ import annotations

import copy
import math
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "contracts/discovery-harness/sheaf-laplacian-employment-result.yaml"

SCHEMA_VERSION = "sheaf-laplacian-employment/v1"
B_EXPECTED = 1000
SEED_EXPECTED = 42
NULL_MODEL_EXPECTED = "stratified-label-permutation"
ALPHA = 0.05
REDUNDANCY_GATE = 0.95
VERDICTS = {"additive", "redundant", "negative"}
SUBSTRATES = {"bhps", "integration"}
FAMILIES = ("nssec", "cohort")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# A4 anchors for the fixture payload. Injected, never read from disk.
FIXTURE_ANCHORS: dict[tuple[str, str, str], int] = {
    ("bhps", "nssec", "Professional/Managerial"): 335,
    ("bhps", "nssec", "Routine/Manual"): 2620,
    ("bhps", "cohort", "1960s"): 1722,
    ("bhps", "cohort", "1980s"): 223,
}


def _require_exact_type(value: object, expected: type, field: str) -> None:
    if type(value) is not expected:
        raise ValueError(f"{field} must have type {expected.__name__}")


def _require_finite_number(value: object, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field} must be finite")


def _bh_adjust(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values (step-up, monotonised, capped at 1).

    Re-derived here independently of the battery so the stored ``p_fdr`` values are
    checked rather than trusted: a corrupted p_fdr could otherwise flip the verdict
    while still sitting inside [1/(B+1), 1].
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        running = min(running, min(1.0, p_values[idx] * m / (rank + 1)))
        adjusted[idx] = running
    return adjusted


def _recompute_verdict(rows: list[dict[str, Any]]) -> str:
    """Locked decision rule, recomputed from stored p_fdr and rho values."""
    rejects = [float(r["p_fdr"]) <= ALPHA for r in rows]
    if not any(rejects):
        return "negative"
    for family in FAMILIES:
        fam = [r for r in rows if r["family"] == family]
        if not fam:
            continue
        gates_ok = all(
            abs(float(r["rho_chi2"])) < REDUNDANCY_GATE and abs(float(r["rho_js"])) < REDUNDANCY_GATE for r in fam
        )
        if all(float(r["p_fdr"]) <= ALPHA for r in fam) and gates_ok:
            return "additive"
    return "redundant"


def validate_sheaf_laplacian_employment_result(
    payload: dict[str, Any],
    anchors: dict[tuple[str, str, str], int] | None = None,
) -> None:
    """Validate a sheaf-energy battery result against the LOCKED pre-registration.

    Args:
        payload: The result JSON as a dict.
        anchors: ``(substrate, family, label) -> n`` T1.28 checkpoint anchors.
            Only labels present here are anchor-checked ("where checkpoints exist").

    Raises:
        ValueError: On any contract violation.
    """
    anchors = anchors or {}

    required = {
        "schema_version",
        "substrate_sha256",
        "params",
        "families",
        "null_model_construction_verified",
        "decision",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"missing required top-level keys: {sorted(missing)}")

    # (b) schema_version
    _require_exact_type(payload["schema_version"], str, "schema_version")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version must equal {SCHEMA_VERSION!r}")

    # (l) substrate provenance
    sha_map = payload["substrate_sha256"]
    _require_exact_type(sha_map, dict, "substrate_sha256")
    for substrate in SUBSTRATES:
        if substrate not in sha_map:
            raise ValueError(f"substrate_sha256 missing the {substrate!r} entry")
        if not SHA256_RE.match(str(sha_map[substrate])):
            raise ValueError(f"substrate_sha256[{substrate!r}] must be a 64-hex sha256")

    # (c)(d)(e) locked params
    params = payload["params"]
    _require_exact_type(params, dict, "params")
    _require_exact_type(params.get("B"), int, "params.B")
    if params["B"] != B_EXPECTED:
        raise ValueError(f"params.B must equal the pre-registered {B_EXPECTED}")
    _require_exact_type(params.get("seed"), int, "params.seed")
    if params["seed"] != SEED_EXPECTED:
        raise ValueError(f"params.seed must equal the pre-registered {SEED_EXPECTED}")
    _require_exact_type(params.get("null_model"), str, "params.null_model")
    if params["null_model"] != NULL_MODEL_EXPECTED:
        raise ValueError(f"params.null_model must equal {NULL_MODEL_EXPECTED!r}")

    # (f) null construction verified
    _require_exact_type(payload["null_model_construction_verified"], bool, "null_model_construction_verified")
    if payload["null_model_construction_verified"] is not True:
        raise ValueError("null_model_construction_verified must be true")

    # (a) families payload — exactly the locked 4-cell family x substrate matrix.
    # The locked rule quantifies over BOTH substrates per family, so a missing,
    # duplicated, or unknown cell has no defined verdict; without this, a payload
    # carrying one nssec row would let `all(...)` vacuously return ADDITIVE off a
    # single substrate.
    rows = payload["families"]
    _require_exact_type(rows, list, "families")
    expected_cells = {(family, substrate) for family in FAMILIES for substrate in SUBSTRATES}
    seen_cells: list[tuple[str, str]] = []

    p_floor = 1.0 / (B_EXPECTED + 1)
    for row in rows:
        _require_exact_type(row, dict, "families[]")
        for key in (
            "family",
            "substrate",
            "p_upper",
            "p_lower",
            "p_fdr",
            "rho_chi2",
            "rho_js",
            "effect_size",
            "group_ns",
        ):
            if key not in row:
                raise ValueError(f"families[] missing {key!r}")
        _require_exact_type(row.get("family"), str, "families[].family")
        _require_exact_type(row.get("substrate"), str, "families[].substrate")
        if row["substrate"] not in SUBSTRATES:
            raise ValueError(f"families[].substrate {row['substrate']!r} is not a known substrate")
        if row["family"] not in FAMILIES:
            raise ValueError(f"families[].family {row['family']!r} is not a locked family")
        seen_cells.append((row["family"], row["substrate"]))

        # (g) p-value range
        for key in ("p_upper", "p_lower", "p_fdr"):
            _require_finite_number(row[key], f"families[].{key}")
            value = float(row[key])
            if not (p_floor <= value <= 1.0):
                raise ValueError(f"families[].{key}={value} outside [1/(B+1), 1] = [{p_floor}, 1]")

        # (h) correlation range
        for key in ("rho_chi2", "rho_js"):
            _require_finite_number(row[key], f"families[].{key}")
            if abs(float(row[key])) > 1.0:
                raise ValueError(f"families[].{key} must satisfy abs(rho) <= 1")

        _require_finite_number(row["effect_size"], "families[].effect_size")

        # (k) A4 anchors where checkpoints exist
        group_ns = row["group_ns"]
        _require_exact_type(group_ns, dict, "families[].group_ns")
        for label, n_value in group_ns.items():
            _require_exact_type(n_value, int, f"families[].group_ns[{label!r}]")
            anchor = anchors.get((row["substrate"], row["family"], label))
            if anchor is not None and int(n_value) != anchor:
                raise ValueError(
                    f"group n for {row['substrate']}/{row['family']}/{label} is {n_value} "
                    f"but the T1.28 checkpoint anchor is {anchor}"
                )

    if len(seen_cells) != len(expected_cells) or set(seen_cells) != expected_cells:
        raise ValueError(
            "families must contain exactly one row per locked family x substrate cell; "
            f"expected {sorted(expected_cells)}, got {sorted(seen_cells)}"
        )

    # BH-FDR is recomputed from p_upper and compared with the stored p_fdr, rather
    # than trusted: the verdict is a function of p_fdr, so an unchecked p_fdr is an
    # unenforced statistical claim.
    recomputed_fdr = _bh_adjust([float(r["p_upper"]) for r in rows])
    for row, expected in zip(rows, recomputed_fdr):
        if not math.isclose(float(row["p_fdr"]), expected, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError(
                f"families[{row['family']}/{row['substrate']}].p_fdr={row['p_fdr']} does not match BH-FDR "
                f"recomputed from the stored p_upper values ({expected})"
            )

    # (i)(j) decision
    decision = payload["decision"]
    _require_exact_type(decision, dict, "decision")
    verdict = decision.get("verdict")
    if verdict not in VERDICTS:
        raise ValueError(f"decision.verdict must be one of {sorted(VERDICTS)}")
    recomputed = _recompute_verdict(rows)
    if verdict != recomputed:
        raise ValueError(
            f"decision.verdict {verdict!r} is inconsistent with the locked rule (recomputed {recomputed!r})"
        )


def _valid_payload() -> dict[str, Any]:
    """A conforming payload: both families reject on both substrates, gates pass -> additive."""
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        for substrate in ("bhps", "integration"):
            if substrate == "bhps" and family == "nssec":
                group_ns = {"Professional/Managerial": 335, "Routine/Manual": 2620, "Intermediate": 1790}
            elif substrate == "bhps" and family == "cohort":
                group_ns = {"1960s": 1722, "1980s": 223}
            else:
                group_ns = {"Professional/Managerial": 2407, "Routine/Manual": 10158}
            rows.append(
                {
                    "family": family,
                    "substrate": substrate,
                    "p_upper": 0.000999000999000999,
                    "p_lower": 1.0,
                    # BH over four identical p_upper values leaves them unchanged —
                    # matching the real battery output (p_upper=0.0010, p_fdr=0.0010).
                    "p_fdr": 0.000999000999000999,
                    "rho_chi2": 0.24,
                    "rho_js": 0.18,
                    "effect_size": 9.7,
                    "group_ns": group_ns,
                }
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "substrate_sha256": {
            "bhps": "b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490",
            "integration": "7a4869170bb8c0f096c407a636ec09ee1926946372b27c18762734d96059e3b8",
        },
        "params": {"B": 1000, "seed": 42, "null_model": "stratified-label-permutation"},
        "families": rows,
        "null_model_construction_verified": True,
        "decision": {"verdict": "additive", "rationale": "both families reject with gates passing"},
    }


def test_contract_file_matches_the_binding() -> None:
    """The contract on disk must point at this test function and pin these values."""
    contract = yaml.safe_load(CONTRACT_PATH.read_text())

    assert contract["id"] == "sheaf-laplacian-employment-result"
    assert contract["kind"] == "schema"
    assert contract["binding"]["test_file"] == "tests/discovery/test_sheaf_laplacian_employment_contract.py"
    assert contract["binding"]["test_function"] == "test_sheaf_result_rejects_invalid_payloads"
    assert contract["schema_def"]["applies_to"] == "results/trajectory_tda_sheaf/sheaf_laplacian_employment_*.json"
    declared = {key["name"] for key in contract["schema_def"]["required_keys"]}
    assert declared == {
        "schema_version",
        "substrate_sha256",
        "params",
        "families",
        "null_model_construction_verified",
        "decision",
    }


def test_sheaf_result_rejects_invalid_payloads() -> None:
    """Bound test for sheaf-laplacian-employment-result.

    Accepts a conforming payload and rejects each pre-registered violation.
    """
    # Accepts the conforming payload, with and without anchor injection.
    validate_sheaf_laplacian_employment_result(_valid_payload())
    validate_sheaf_laplacian_employment_result(_valid_payload(), anchors=FIXTURE_ANCHORS)

    # (a) required top-level evidence is missing
    for key in (
        "schema_version",
        "substrate_sha256",
        "params",
        "families",
        "null_model_construction_verified",
        "decision",
    ):
        payload = _valid_payload()
        del payload[key]
        with pytest.raises(ValueError, match="missing required top-level keys"):
            validate_sheaf_laplacian_employment_result(payload)

    # (b) schema_version differs
    payload = _valid_payload()
    payload["schema_version"] = "sheaf-laplacian-employment/v2"
    with pytest.raises(ValueError, match="schema_version must equal"):
        validate_sheaf_laplacian_employment_result(payload)

    # (c) params.B differs from 1000
    payload = _valid_payload()
    payload["params"]["B"] = 199
    with pytest.raises(ValueError, match="params.B must equal"):
        validate_sheaf_laplacian_employment_result(payload)

    # (d) params.seed differs from 42, or has the wrong type
    payload = _valid_payload()
    payload["params"]["seed"] = 7
    with pytest.raises(ValueError, match="params.seed must equal"):
        validate_sheaf_laplacian_employment_result(payload)

    payload = _valid_payload()
    payload["params"]["seed"] = "42"
    with pytest.raises(ValueError, match="params.seed must have type int"):
        validate_sheaf_laplacian_employment_result(payload)

    # (e) params.null_model differs
    payload = _valid_payload()
    payload["params"]["null_model"] = "markov-1-pooled"
    with pytest.raises(ValueError, match="params.null_model must equal"):
        validate_sheaf_laplacian_employment_result(payload)

    # (f) null_model_construction_verified is not true
    payload = _valid_payload()
    payload["null_model_construction_verified"] = False
    with pytest.raises(ValueError, match="null_model_construction_verified must be true"):
        validate_sheaf_laplacian_employment_result(payload)

    # (g) p_upper / p_lower outside [1/(B+1), 1]
    for key, bad in (("p_upper", 0.0), ("p_lower", 1.5), ("p_upper", 1e-9)):
        payload = _valid_payload()
        payload["families"][0][key] = bad
        with pytest.raises(ValueError, match="outside"):
            validate_sheaf_laplacian_employment_result(payload)

    # (h) abs(rho) exceeds 1
    for key in ("rho_chi2", "rho_js"):
        payload = _valid_payload()
        payload["families"][0][key] = 1.2
        with pytest.raises(ValueError, match="abs\\(rho\\) <= 1"):
            validate_sheaf_laplacian_employment_result(payload)

    # (i) verdict outside the locked vocabulary
    payload = _valid_payload()
    payload["decision"]["verdict"] = "partial-signal"
    with pytest.raises(ValueError, match="decision.verdict must be one of"):
        validate_sheaf_laplacian_employment_result(payload)

    # (j) verdict inconsistent with the locked rule recomputed from stored values.
    # Rejections stand but a redundancy gate fails everywhere -> redundant, not additive.
    payload = _valid_payload()
    for row in payload["families"]:
        row["rho_chi2"] = 0.99
    with pytest.raises(ValueError, match="inconsistent with the locked rule"):
        validate_sheaf_laplacian_employment_result(payload)

    # No rejections at all -> negative, not additive. p_upper and p_fdr move together
    # so the payload stays BH-consistent and the verdict check is what fires.
    payload = _valid_payload()
    for row in payload["families"]:
        row["p_upper"] = 0.4
        row["p_fdr"] = 0.4
    with pytest.raises(ValueError, match="inconsistent with the locked rule"):
        validate_sheaf_laplacian_employment_result(payload)

    # A p_fdr that does not follow from the stored p_upper values is rejected on its
    # own, before any verdict question — an unchecked p_fdr is an unenforced claim.
    payload = _valid_payload()
    payload["families"][0]["p_fdr"] = 0.9
    with pytest.raises(ValueError, match="does not match BH-FDR"):
        validate_sheaf_laplacian_employment_result(payload)

    # Exactly the locked 4-cell matrix: a dropped cell, a duplicate, and an unknown
    # family are all rejected (a single nssec row would otherwise vacuously satisfy
    # "rejects on both substrates").
    payload = _valid_payload()
    payload["families"] = [r for r in payload["families"] if r["family"] == "nssec" and r["substrate"] == "bhps"]
    with pytest.raises(ValueError, match="exactly one row per locked family"):
        validate_sheaf_laplacian_employment_result(payload)

    payload = _valid_payload()
    payload["families"].append(copy.deepcopy(payload["families"][0]))
    with pytest.raises(ValueError, match="exactly one row per locked family"):
        validate_sheaf_laplacian_employment_result(payload)

    payload = _valid_payload()
    payload["families"][0]["family"] = "gender"
    with pytest.raises(ValueError, match="is not a locked family"):
        validate_sheaf_laplacian_employment_result(payload)

    # (k) a group n contradicts its A4 checkpoint anchor
    payload = _valid_payload()
    payload["families"][0]["group_ns"]["Professional/Managerial"] = 336
    with pytest.raises(ValueError, match="T1.28 checkpoint anchor"):
        validate_sheaf_laplacian_employment_result(payload, anchors=FIXTURE_ANCHORS)

    # (l) substrate_sha256 missing an entry
    for substrate in ("bhps", "integration"):
        payload = _valid_payload()
        del payload["substrate_sha256"][substrate]
        with pytest.raises(ValueError, match=f"missing the '{substrate}' entry"):
            validate_sheaf_laplacian_employment_result(payload)

    # (m) contract-pinned values supplied with the wrong type
    payload = _valid_payload()
    payload["params"]["B"] = "1000"
    with pytest.raises(ValueError, match="params.B must have type int"):
        validate_sheaf_laplacian_employment_result(payload)

    payload = _valid_payload()
    payload["null_model_construction_verified"] = "true"
    with pytest.raises(ValueError, match="null_model_construction_verified must have type bool"):
        validate_sheaf_laplacian_employment_result(payload)

    payload = _valid_payload()
    payload["families"][0]["group_ns"]["Professional/Managerial"] = 335.0
    with pytest.raises(ValueError, match="must have type int"):
        validate_sheaf_laplacian_employment_result(payload)

    # The unmutated fixture still validates — the mutations above are the only cause.
    validate_sheaf_laplacian_employment_result(copy.deepcopy(_valid_payload()), anchors=FIXTURE_ANCHORS)
