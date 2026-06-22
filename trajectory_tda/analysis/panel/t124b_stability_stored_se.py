# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Binomial standard error and Wilson 95% CI for the Table 2 stored
#          stability proportion per GMM regime (reviewer B10). Recomputes the
#          SE on the HEADLINE stability_stored metric, fixing the declared-vs-
#          computed mismatch in stability_se_2026-05-16.json (SE on from_seqs).
"""Stored-metric stability standard error for P01-A Table 2 (reviewer B10).

The prior file ``stability_se_2026-05-16.json`` declared
``use_stability: "stability_stored"`` canonical but computed its ``SE``/``CI95``
on ``stability_from_seqs`` (the within-trajectory diagnostic). This module
recomputes, per regime, the binomial standard error of the *stored* proportion::

    SE = sqrt(p * (1 - p) / n_members)

with a Wilson 95% confidence interval, matching the reviewer's formula and
worked examples. The headline denominator is ``n_members`` (reviewer
correspondence); the window-pair denominator (``n_transitions``) is reported as
a tighter alternative for transparency only.

Run from the task worktree root::

    uv run --env-file .env python -m trajectory_tda.analysis.panel.t124b_stability_stored_se
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Mapping

PROJ_ROOT = Path("C:/Users/steph/TDL")
WORKTREE = Path.cwd()

DEFAULT_SOURCE = WORKTREE / "results/panel_methodology/uncertainty_addons/stability_se_2026-05-16.json"
DEFAULT_OUT_DIR = WORKTREE / "results/panel_methodology/uncertainty_addons"

SCHEMA_VERSION = "stability-stored-se-v1"
COMPUTED_ON = "stability_stored"
SUPERSEDED_FILE = "results/panel_methodology/uncertainty_addons/stability_se_2026-05-16.json"
# norm.ppf(0.975); kept as a literal to avoid a scipy import for one constant.
Z_95 = 1.959963984540054
SE_TOL = 1e-4


def binomial_se(p: float, n: int) -> float:
    """Return the binomial standard error sqrt(p*(1-p)/n)."""

    return math.sqrt(p * (1.0 - p) / n)


def wilson_ci(p: float, n: int, z: float = Z_95) -> tuple[float, float]:
    """Return the Wilson score 95% confidence interval for a proportion.

    Args:
        p: Observed proportion in [0, 1].
        n: Number of trials (denominator).
        z: Standard-normal quantile (default 1.96 for 95%).

    Returns:
        Ordered (lower, upper) interval bounds.
    """

    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return centre - half, centre + half


def compute_stored_se(source: Path = DEFAULT_SOURCE) -> dict[str, Any]:
    """Compute per-regime stored-metric SE and Wilson CI from the prior file."""

    with source.open("r", encoding="utf-8") as handle:
        prior = json.load(handle)

    stability_by_regime: dict[str, Any] = {}
    for regime_key, block in prior["stability_by_regime"].items():
        stored = float(block["stability_stored"])
        n_members = int(block["n_members"])
        n_transitions = int(block["n_transitions"])
        se = binomial_se(stored, n_members)
        lo, hi = wilson_ci(stored, n_members)
        stability_by_regime[regime_key] = {
            "regime": int(block["regime"]),
            "stability_stored": stored,
            "n_members": n_members,
            "SE": se,
            "CI95_lo": lo,
            "CI95_hi": hi,
            "CI95_method": "Wilson score interval",
            # Tighter window-pair alternative, for transparency only.
            "n_transitions": n_transitions,
            "SE_window_pair_alt": binomial_se(stored, n_transitions),
        }

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": date.today().isoformat(),
        "computed_on": COMPUTED_ON,
        "supersedes": {
            "file": SUPERSEDED_FILE,
            "column": "SE / CI95 (Table 2 stability uncertainty column)",
            "reason": (
                "The prior SE/CI95 were computed on stability_from_seqs (the "
                "within-trajectory state-stickiness diagnostic), not the declared "
                "canonical stability_stored (window-pair regime stickiness)."
            ),
            "do_not_cite_for_table2": True,
            "retained_valid": (
                "The stability_stored point values in that file remain valid; "
                "only its SE/CI95 column is superseded for Table 2."
            ),
        },
        "source_file": str(source),
        "method": (
            "Per regime, SE = sqrt(stored*(1-stored)/n_members) on the Table 2 "
            "stability_stored proportion, with a Wilson 95% confidence interval "
            "on the stored proportion. Headline denominator is n_members "
            "(reviewer correspondence); n_transitions gives a tighter alternative."
        ),
        "denominator": "n_members",
        "stability_by_regime": stability_by_regime,
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    """Machine-check stored-SE output invariants required by the contract."""

    required_top = {
        "schema_version",
        "created_at",
        "computed_on",
        "supersedes",
        "source_file",
        "method",
        "stability_by_regime",
    }
    assert "stability_from_seqs_se" not in payload, "forbidden key stability_from_seqs_se present at top level"
    missing_top = required_top - set(payload)
    assert not missing_top, f"missing required top-level keys: {sorted(missing_top)}"

    assert payload["schema_version"] == SCHEMA_VERSION
    # R3 self-description lock: declared metric must be the stored proportion.
    assert payload["computed_on"] == COMPUTED_ON, f"computed_on must be '{COMPUTED_ON}'"

    supersedes = payload["supersedes"]
    assert isinstance(supersedes, Mapping)
    assert (
        supersedes["file"]
        .replace("\\", "/")
        .endswith("results/panel_methodology/uncertainty_addons/stability_se_2026-05-16.json")
    )
    assert supersedes["do_not_cite_for_table2"] is True

    assert (
        payload["source_file"]
        .replace("\\", "/")
        .endswith("results/panel_methodology/uncertainty_addons/stability_se_2026-05-16.json")
    )
    assert "sqrt" in payload["method"] and "Wilson" in payload["method"]

    regimes = payload["stability_by_regime"]
    assert len(regimes) >= 1
    for regime_key, block in regimes.items():
        assert "stability_from_seqs_se" not in block, f"forbidden key stability_from_seqs_se present in {regime_key}"
        stored = float(block["stability_stored"])
        n_members = int(block["n_members"])
        assert 0.0 <= stored <= 1.0, f"{regime_key}: stability_stored out of [0,1]"
        assert n_members > 0, f"{regime_key}: n_members must be > 0"
        se = float(block["SE"])
        assert se >= 0.0, f"{regime_key}: SE negative"
        expected_se = binomial_se(stored, n_members)
        assert abs(se - expected_se) <= SE_TOL, f"{regime_key}: SE {se} != sqrt(p(1-p)/n) {expected_se} within {SE_TOL}"
        lo = float(block["CI95_lo"])
        hi = float(block["CI95_hi"])
        assert lo <= hi, f"{regime_key}: CI95 bounds unordered"


def validate_stability_stored_se_output(payload: Mapping[str, Any]) -> None:
    """Validate a stored-SE output payload against the local contract."""

    validate_payload(dict(payload))


def dispatch_t124b_json(path: Path, payload: Mapping[str, Any]) -> bool:
    """Route stored-SE JSONs; leave the legacy stability_se files untouched.

    Returns True only for ``stability_se_stored_*.json`` files under
    ``results/panel_methodology/uncertainty_addons/``. The legacy
    ``stability_se_2026-05-16.json`` / ``stability_se_2026-05-14.json`` files are
    not captured.
    """

    rel = path.as_posix()
    if (
        path.name.startswith("stability_se_stored_")
        and path.suffix == ".json"
        and "results/panel_methodology/uncertainty_addons/" in rel
    ):
        validate_stability_stored_se_output(payload)
        return True
    return False


def write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON result, refusing to overwrite an existing file."""

    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing result: {path}")
    assert path.name == f"stability_se_stored_{payload['created_at']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_payload(payload)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_path = args.out_dir / f"stability_se_stored_{args.date}.json"
    print("=== Stored-metric stability SE (Table 2, reviewer B10) ===")
    print(f"Source: {args.source}")
    print(f"Output: {out_path}")
    payload = compute_stored_se(source=args.source)
    write_json_no_overwrite(out_path, payload)
    for regime_key, block in payload["stability_by_regime"].items():
        print(
            f"  {regime_key}: stored={block['stability_stored']:.4f} "
            f"n={block['n_members']} SE={block['SE']:.4f} "
            f"CI95=[{block['CI95_lo']:.4f}, {block['CI95_hi']:.4f}]"
        )
    print("=== complete ===")


if __name__ == "__main__":
    main()
