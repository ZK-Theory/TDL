# Research context: TDA-Research/00-Meta/Discovery/mcbif-weighted-nerve-employment-dispatch-prereg-2026-07-10.md
# Purpose: Binding test for contracts/discovery-harness/mcbif-weighted-nerve-employment-result.yaml.
#   Hermetic by construction — payloads are synthetic fixtures; nothing is read
#   from PROJ_ROOT, so the test cannot fail merely because a gitignored
#   intermediate is absent from a fresh worktree.
"""Binding tests for the LOCKED weighted-nerve employment battery result contract."""

from __future__ import annotations

import copy
import math
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "contracts/discovery-harness/mcbif-weighted-nerve-employment-result.yaml"

SCHEMA_VERSION = "mcbif-weighted-nerve-employment/v1"
TAU_EXPECTED = 2
B_EXPECTED = 1000
SEED_EXPECTED = 42
W_EXPECTED = 13
TEST_EXPECTED = "two-sided"
PER_DRAW_EXPECTED = "42+b for b in 0..999"
ALPHA = 0.05
REDUNDANCY_GATE = 0.95
VERDICTS = {"additive", "partial-signal", "redundant", "negative"}
ARMS = ("integration", "bhps")
PRIMARY = "h1_total_area"
REQUIRED_STATS = ("h1_total_area", "h1_lag2_area", "h1_lag3_area", "h1_lag_weighted_area")
LOCKED_SHA = {
    "integration": "7a4869170bb8c0f096c407a636ec09ee1926946372b27c18762734d96059e3b8",
    "bhps": "b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
P_FLOOR = 1.0 / (B_EXPECTED + 1)


def _require_exact_type(value: object, expected: type, field: str) -> None:
    if type(value) is not expected:
        raise ValueError(f"{field} must have type {expected.__name__}")


def _require_finite_number(value: object, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field} must be finite")


def _bh_adjust(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg step-up adjusted p-values, re-derived independently.

    The stored ``p_fdr`` pair is checked against this rather than trusted: a
    corrupted p_fdr could flip the verdict while sitting inside [1/(B+1), 1].
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


def _recompute_verdict(payload: dict[str, Any]) -> str:
    """Locked decision rule recomputed from stored p_fdr and redundancy values.

    An arm's rejection is primary p_fdr <= alpha; its gates pass when both
    |rho| < 0.95; an "effective" rejection is both. ADDITIVE: effective on both
    substrates. NEGATIVE: no rejection anywhere. REDUNDANT: rejections exist
    but none survive its arm's gates. PARTIAL-SIGNAL: exactly one effective
    rejection. (Matches decide_verdict in the battery script.)
    """
    rejected = {}
    effective = {}
    for arm in ARMS:
        p_fdr = float(payload["null_distribution"][arm][PRIMARY]["p_fdr"])
        red = payload["redundancy"][arm]
        gates = abs(float(red["rho_ari"])) < REDUNDANCY_GATE and abs(float(red["rho_ce"])) < REDUNDANCY_GATE
        rejected[arm] = p_fdr <= ALPHA
        effective[arm] = rejected[arm] and gates
    if all(effective.values()):
        return "additive"
    if not any(rejected.values()):
        return "negative"
    if not any(effective.values()):
        return "redundant"
    return "partial-signal"


def validate_mcbif_weighted_nerve_result(payload: dict[str, Any]) -> None:
    """Validate a battery result JSON against the LOCKED pre-registration.

    Args:
        payload: The result JSON as a dict.

    Raises:
        ValueError: On any contract violation.
    """
    # (a) required top-level evidence
    required = {
        "schema_version",
        "substrate_sha256",
        "params",
        "gate0",
        "observed",
        "null_distribution",
        "redundancy",
        "decision",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"missing required top-level keys: {sorted(missing)}")

    # (b) schema_version
    _require_exact_type(payload["schema_version"], str, "schema_version")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version must equal {SCHEMA_VERSION!r}")

    # (m) substrate provenance — both arms, locked digests
    sha_map = payload["substrate_sha256"]
    _require_exact_type(sha_map, dict, "substrate_sha256")
    for arm in ARMS:
        if arm not in sha_map:
            raise ValueError(f"substrate_sha256 missing the {arm!r} entry")
        digest = sha_map[arm]
        _require_exact_type(digest, str, f"substrate_sha256[{arm!r}]")
        if not SHA256_RE.match(digest) or digest != LOCKED_SHA[arm]:
            raise ValueError(f"substrate_sha256[{arm!r}] must equal the locked digest {LOCKED_SHA[arm]}")

    # (c)-(g), (p) locked params
    params = payload["params"]
    _require_exact_type(params, dict, "params")
    for name, expected in (
        ("tau", TAU_EXPECTED),
        ("B", B_EXPECTED),
        ("seed", SEED_EXPECTED),
        ("W", W_EXPECTED),
    ):
        _require_exact_type(params.get(name), int, f"params.{name}")
        if params[name] != expected:
            raise ValueError(f"params.{name} must equal the pre-registered {expected}")
    _require_exact_type(params.get("test"), str, "params.test")
    if params["test"] != TEST_EXPECTED:
        raise ValueError(f"params.test must equal {TEST_EXPECTED!r}")
    # The per-draw seed schedule declaration must match the pre-registered
    # default_rng(42+b).permutation(13) schedule exactly. The declaration is
    # enforced here; the schedule itself is enforced against the canonical
    # generator by tests/discovery/test_mcbif_weighted_nerve_battery.py::
    # test_null_orderings_are_the_preregistered_draws.
    _require_exact_type(params.get("per_draw_seeds"), str, "params.per_draw_seeds")
    if params["per_draw_seeds"] != PER_DRAW_EXPECTED:
        raise ValueError(f"params.per_draw_seeds must equal the pre-registered {PER_DRAW_EXPECTED!r}")

    # (o) gate0 per arm
    gate0 = payload["gate0"]
    _require_exact_type(gate0, dict, "gate0")
    for arm in ARMS:
        if arm not in gate0:
            raise ValueError(f"gate0 missing the {arm!r} entry")
        rec = gate0[arm]
        _require_exact_type(rec, dict, f"gate0[{arm!r}]")
        for key in ("complete_adjacent_fraction", "observed_h1_total_area", "infeasible"):
            if key not in rec:
                raise ValueError(f"gate0[{arm!r}] missing {key!r}")
        _require_exact_type(rec["infeasible"], bool, f"gate0[{arm!r}].infeasible")
        _require_finite_number(rec["complete_adjacent_fraction"], f"gate0[{arm!r}].complete_adjacent_fraction")
        _require_finite_number(rec["observed_h1_total_area"], f"gate0[{arm!r}].observed_h1_total_area")
        if rec["infeasible"]:
            # A Gate-0 failing arm is INFEASIBLE per the pre-reg: it escalates,
            # and the v1 verdict vocabulary has no escalation state — so an
            # assembled payload carrying an infeasible arm is invalid outright.
            raise ValueError(f"gate0[{arm!r}] is Gate-0 infeasible — BLOCKED arms escalate; no assembled verdict")
        if float(rec["complete_adjacent_fraction"]) >= 0.9:
            raise ValueError(f"gate0[{arm!r}] complete_adjacent_fraction >= 0.9 for an arm not marked infeasible")
        if float(rec["observed_h1_total_area"]) <= 0:
            raise ValueError(f"gate0[{arm!r}] observed h1_total_area <= 0 for an arm not marked infeasible")

    # observed: all four pre-registered H1 statistics per arm
    observed = payload["observed"]
    _require_exact_type(observed, dict, "observed")
    for arm in ARMS:
        if arm not in observed:
            raise ValueError(f"observed missing the {arm!r} entry")
        for stat in REQUIRED_STATS:
            if stat not in observed[arm]:
                raise ValueError(f"observed[{arm!r}] missing {stat!r}")
            _require_finite_number(observed[arm][stat], f"observed[{arm!r}][{stat!r}]")

    # (h)(i) null distribution per arm x statistic
    nulls = payload["null_distribution"]
    _require_exact_type(nulls, dict, "null_distribution")
    for arm in ARMS:
        if arm not in nulls:
            raise ValueError(f"null_distribution missing the {arm!r} entry")
        block = nulls[arm]
        _require_exact_type(block, dict, f"null_distribution[{arm!r}]")
        for stat in REQUIRED_STATS:
            if stat not in block:
                raise ValueError(f"null_distribution[{arm!r}] missing {stat!r}")
        for stat, entry in block.items():
            _require_exact_type(entry, dict, f"null_distribution[{arm!r}][{stat!r}]")
            for key in ("p_lower", "p_upper", "p_two"):
                if key not in entry:
                    raise ValueError(f"null_distribution[{arm!r}][{stat!r}] missing {key!r}")
                _require_finite_number(entry[key], f"null_distribution[{arm!r}][{stat!r}].{key}")
                value = float(entry[key])
                if not (P_FLOOR <= value <= 1.0):
                    raise ValueError(
                        f"null_distribution[{arm!r}][{stat!r}].{key}={value} outside [1/(B+1), 1] = [{P_FLOOR}, 1]"
                    )
            recomputed = min(1.0, 2.0 * min(float(entry["p_lower"]), float(entry["p_upper"])))
            if not math.isclose(float(entry["p_two"]), recomputed, rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError(
                    f"null_distribution[{arm!r}][{stat!r}].p_two={entry['p_two']} is not "
                    f"min(1, 2*min(p_lower, p_upper)) = {recomputed} from the stored tails"
                )
        if "p_fdr" not in block[PRIMARY]:
            raise ValueError(f"null_distribution[{arm!r}][{PRIMARY!r}] missing 'p_fdr'")
        _require_finite_number(block[PRIMARY]["p_fdr"], f"null_distribution[{arm!r}][{PRIMARY!r}].p_fdr")

    # (j) the primary p_fdr pair recomputes via BH-FDR from the stored p_two pair
    p_two_pair = [float(nulls[arm][PRIMARY]["p_two"]) for arm in ARMS]
    expected_fdr = _bh_adjust(p_two_pair)
    for arm, expected in zip(ARMS, expected_fdr):
        stored = float(nulls[arm][PRIMARY]["p_fdr"])
        if not math.isclose(stored, expected, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError(
                f"null_distribution[{arm!r}][{PRIMARY!r}].p_fdr={stored} does not match BH-FDR "
                f"recomputed from the stored per-substrate p_two pair ({expected})"
            )

    # (n) redundancy gates per arm
    redundancy = payload["redundancy"]
    _require_exact_type(redundancy, dict, "redundancy")
    for arm in ARMS:
        if arm not in redundancy:
            raise ValueError(f"redundancy missing the {arm!r} entry")
        rec = redundancy[arm]
        _require_exact_type(rec, dict, f"redundancy[{arm!r}]")
        for key in ("rho_ari", "rho_ce"):
            if key not in rec:
                raise ValueError(f"redundancy[{arm!r}] missing {key!r}")
            _require_finite_number(rec[key], f"redundancy[{arm!r}].{key}")
            if abs(float(rec[key])) > 1.0:
                raise ValueError(f"redundancy[{arm!r}].{key} must satisfy abs(rho) <= 1")

    # (k)(l) decision
    decision = payload["decision"]
    _require_exact_type(decision, dict, "decision")
    verdict = decision.get("verdict")
    if verdict not in VERDICTS:
        raise ValueError(f"decision.verdict must be one of {sorted(VERDICTS)}")
    recomputed_verdict = _recompute_verdict(payload)
    if verdict != recomputed_verdict:
        raise ValueError(
            f"decision.verdict {verdict!r} is inconsistent with the locked rule (recomputed {recomputed_verdict!r})"
        )

    # (n) redundancy gate breach on a claimed rejection: an arm whose rejection the
    # verdict relies on must have both gates passing. Covered structurally by the
    # verdict recomputation above (effective-rejection definition); additionally,
    # an additive verdict with any gate breached anywhere is rejected outright.
    if verdict == "additive":
        for arm in ARMS:
            rec = redundancy[arm]
            if abs(float(rec["rho_ari"])) >= REDUNDANCY_GATE or abs(float(rec["rho_ce"])) >= REDUNDANCY_GATE:
                raise ValueError(f"additive verdict with redundancy gate breached on {arm!r}")


def _valid_payload() -> dict[str, Any]:
    """A conforming payload: both arms reject with gates passing -> additive."""
    p_upper = P_FLOOR  # 1/1001, the permutation floor
    p_two = min(1.0, 2.0 * p_upper)
    stats_block = {}
    for stat in REQUIRED_STATS:
        stats_block[stat] = {"p_lower": 1.0, "p_upper": p_upper, "p_two": p_two}
    null_distribution: dict[str, Any] = {}
    for arm in ARMS:
        null_distribution[arm] = copy.deepcopy(stats_block)
        # BH over two equal p_two values leaves them unchanged.
        null_distribution[arm][PRIMARY]["p_fdr"] = p_two
    return {
        "schema_version": SCHEMA_VERSION,
        "substrate_sha256": dict(LOCKED_SHA),
        "params": {
            "tau": 2,
            "B": 1000,
            "seed": 42,
            "W": 13,
            "test": "two-sided",
            "per_draw_seeds": PER_DRAW_EXPECTED,
        },
        "gate0": {
            "integration": {
                "complete_adjacent_fraction": 0.3333333333333333,
                "observed_h1_total_area": 1644.0,
                "infeasible": False,
            },
            "bhps": {
                "complete_adjacent_fraction": 0.0,
                "observed_h1_total_area": 400.0,
                "infeasible": False,
            },
        },
        "observed": {
            "integration": {
                "h1_total_area": 1644.0,
                "h1_lag2_area": 138.0,
                "h1_lag3_area": 117.0,
                "h1_lag_weighted_area": 540.6,
            },
            "bhps": {
                "h1_total_area": 400.0,
                "h1_lag2_area": 40.0,
                "h1_lag3_area": 30.0,
                "h1_lag_weighted_area": 120.0,
            },
        },
        "null_distribution": null_distribution,
        "redundancy": {
            "integration": {"rho_ari": 0.36, "rho_ce": -0.37},
            "bhps": {"rho_ari": 0.2, "rho_ce": -0.25},
        },
        "decision": {"verdict": "additive", "rationale": "fixture"},
    }


def test_contract_file_matches_the_binding() -> None:
    """The contract on disk must point at this test function and pin these values."""
    contract = yaml.safe_load(CONTRACT_PATH.read_text())
    assert contract["id"] == "mcbif-weighted-nerve-employment-result"
    assert contract["kind"] == "schema"
    assert contract["binding"]["test_file"] == "tests/discovery/test_mcbif_weighted_nerve_contract.py"
    assert contract["binding"]["test_function"] == "test_weighted_nerve_rejects_invalid_payloads"
    assert contract["schema_def"]["applies_to"] == "results/trajectory_tda_mcbif/mcbif_weighted_nerve_employment_*.json"
    declared = {key["name"] for key in contract["schema_def"]["required_keys"]}
    assert declared == {
        "schema_version",
        "substrate_sha256",
        "params",
        "gate0",
        "observed",
        "null_distribution",
        "redundancy",
        "decision",
    }


def test_weighted_nerve_rejects_invalid_payloads() -> None:
    """Bound test: accepts a conforming payload and rejects each violation (a)-(p)."""
    validate_mcbif_weighted_nerve_result(_valid_payload())

    # (a) required top-level evidence is missing
    for key in (
        "schema_version",
        "substrate_sha256",
        "params",
        "gate0",
        "observed",
        "null_distribution",
        "redundancy",
        "decision",
    ):
        payload = _valid_payload()
        del payload[key]
        with pytest.raises(ValueError, match="missing required top-level keys"):
            validate_mcbif_weighted_nerve_result(payload)

    # (b) schema_version differs
    payload = _valid_payload()
    payload["schema_version"] = "mcbif-weighted-nerve-employment/v2"
    with pytest.raises(ValueError, match="schema_version must equal"):
        validate_mcbif_weighted_nerve_result(payload)

    # (c) tau differs from 2 — LOCKED by the smallest-tau rule
    payload = _valid_payload()
    payload["params"]["tau"] = 5
    with pytest.raises(ValueError, match="params.tau must equal"):
        validate_mcbif_weighted_nerve_result(payload)

    # (d) B differs from 1000
    payload = _valid_payload()
    payload["params"]["B"] = 99
    with pytest.raises(ValueError, match="params.B must equal"):
        validate_mcbif_weighted_nerve_result(payload)

    # (e) seed differs from 42, or has the wrong type
    payload = _valid_payload()
    payload["params"]["seed"] = 7
    with pytest.raises(ValueError, match="params.seed must equal"):
        validate_mcbif_weighted_nerve_result(payload)
    payload = _valid_payload()
    payload["params"]["seed"] = "42"
    with pytest.raises(ValueError, match="params.seed must have type int"):
        validate_mcbif_weighted_nerve_result(payload)

    # (f) W differs from 13
    payload = _valid_payload()
    payload["params"]["W"] = 18
    with pytest.raises(ValueError, match="params.W must equal"):
        validate_mcbif_weighted_nerve_result(payload)

    # (g) test differs from 'two-sided'
    payload = _valid_payload()
    payload["params"]["test"] = "one-sided"
    with pytest.raises(ValueError, match="params.test must equal"):
        validate_mcbif_weighted_nerve_result(payload)

    # per-draw seed schedule missing, or altered from the pre-registered one
    payload = _valid_payload()
    del payload["params"]["per_draw_seeds"]
    with pytest.raises(ValueError, match="params.per_draw_seeds must have type str"):
        validate_mcbif_weighted_nerve_result(payload)
    payload = _valid_payload()
    payload["params"]["per_draw_seeds"] = "43+b for b in 0..999"
    with pytest.raises(ValueError, match="params.per_draw_seeds must equal"):
        validate_mcbif_weighted_nerve_result(payload)
    payload = _valid_payload()
    payload["params"]["per_draw_seeds"] = "42+b for b in 0..98"
    with pytest.raises(ValueError, match="params.per_draw_seeds must equal"):
        validate_mcbif_weighted_nerve_result(payload)

    # (h) a p value outside [1/(B+1), 1]
    for key, bad in (("p_upper", 0.0), ("p_lower", 1.5), ("p_two", 1e-9)):
        payload = _valid_payload()
        payload["null_distribution"]["integration"][PRIMARY][key] = bad
        with pytest.raises(ValueError, match="outside"):
            validate_mcbif_weighted_nerve_result(payload)

    # (i) p_two not recomputable from the stored tails
    payload = _valid_payload()
    payload["null_distribution"]["integration"][PRIMARY]["p_two"] = 0.5
    with pytest.raises(ValueError, match="min\\(1, 2\\*min\\(p_lower, p_upper\\)\\)"):
        validate_mcbif_weighted_nerve_result(payload)

    # (j) p_fdr not recomputable from the stored per-substrate p_two pair
    payload = _valid_payload()
    payload["null_distribution"]["integration"][PRIMARY]["p_fdr"] = 0.9
    with pytest.raises(ValueError, match="does not match BH-FDR"):
        validate_mcbif_weighted_nerve_result(payload)

    # (k) verdict outside the locked vocabulary
    payload = _valid_payload()
    payload["decision"]["verdict"] = "inconclusive"
    with pytest.raises(ValueError, match="decision.verdict must be one of"):
        validate_mcbif_weighted_nerve_result(payload)

    # (l) verdict inconsistent with the locked rule recomputed from stored values:
    # no rejection anywhere (p_two and p_fdr move together, staying BH-consistent)
    # while the payload still claims additive.
    payload = _valid_payload()
    for arm in ARMS:
        block = payload["null_distribution"][arm][PRIMARY]
        block.update({"p_lower": 0.3, "p_upper": 0.75, "p_two": 0.6, "p_fdr": 0.6})
    with pytest.raises(ValueError, match="inconsistent with the locked rule"):
        validate_mcbif_weighted_nerve_result(payload)

    # (m) substrate_sha256 missing an entry, or a digest differing from its lock
    for arm in ARMS:
        payload = _valid_payload()
        del payload["substrate_sha256"][arm]
        with pytest.raises(ValueError, match=f"missing the '{arm}' entry"):
            validate_mcbif_weighted_nerve_result(payload)
    payload = _valid_payload()
    payload["substrate_sha256"]["integration"] = "0" * 64
    with pytest.raises(ValueError, match="locked digest"):
        validate_mcbif_weighted_nerve_result(payload)

    # (n) redundancy gate breached on an arm whose rejection the verdict claims:
    # both arms reject but bhps gates fail -> partial-signal, so a stored
    # 'additive' is rejected via the recomputation.
    payload = _valid_payload()
    payload["redundancy"]["bhps"]["rho_ari"] = 0.99
    with pytest.raises(ValueError, match="inconsistent with the locked rule"):
        validate_mcbif_weighted_nerve_result(payload)
    # ... and abs(rho) > 1 is rejected outright.
    payload = _valid_payload()
    payload["redundancy"]["bhps"]["rho_ce"] = -1.2
    with pytest.raises(ValueError, match="abs\\(rho\\) <= 1"):
        validate_mcbif_weighted_nerve_result(payload)

    # (o) gate0 saturation / trivial-H1 breach on an arm not marked infeasible
    payload = _valid_payload()
    payload["gate0"]["integration"]["complete_adjacent_fraction"] = 0.95
    with pytest.raises(ValueError, match="complete_adjacent_fraction >= 0.9"):
        validate_mcbif_weighted_nerve_result(payload)
    payload = _valid_payload()
    payload["gate0"]["bhps"]["observed_h1_total_area"] = 0.0
    with pytest.raises(ValueError, match="h1_total_area <= 0"):
        validate_mcbif_weighted_nerve_result(payload)

    # ... and a Gate-0 infeasible arm invalidates the assembled payload outright:
    # BLOCKED arms escalate per the pre-reg; no verdict vocabulary covers them.
    payload = _valid_payload()
    payload["gate0"]["bhps"]["infeasible"] = True
    with pytest.raises(ValueError, match="BLOCKED arms escalate"):
        validate_mcbif_weighted_nerve_result(payload)

    # (p) a contract-pinned value supplied as the wrong type
    payload = _valid_payload()
    payload["params"]["B"] = "1000"
    with pytest.raises(ValueError, match="params.B must have type int"):
        validate_mcbif_weighted_nerve_result(payload)
    payload = _valid_payload()
    payload["gate0"]["integration"]["infeasible"] = "false"
    with pytest.raises(ValueError, match="infeasible must have type bool"):
        validate_mcbif_weighted_nerve_result(payload)

    # The unmutated fixture still validates — the mutations above are the only cause.
    validate_mcbif_weighted_nerve_result(copy.deepcopy(_valid_payload()))
