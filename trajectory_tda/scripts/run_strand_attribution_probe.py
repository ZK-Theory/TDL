# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: Tier-1 attribution probe for the STRAND H0 merge-scale asymmetry
#   (T-STRAND-1 follow-up). Reuses EXISTING frozen matched-control diagram
#   caches (no new PH compute) to test whether the USoc>>BHPS H0/H1 lifetime
#   shift survives the project's horizon- and size-matching controls, deciding
#   whether the heavier Tier-2 study (USoc-downsample control) is worth running.
"""Tier-1 STRAND attribution probe (reuse-path; no new persistent homology).

Compares USoc observed persistence-lifetime distributions against three BHPS
variants already cached by Stage-1:
  - raw frozen            (no control)
  - length-matched        (truncate BHPS to the USoc observation horizon)
  - non-overlap           (size/overlap-controlled BHPS subsample)

For each contrast and homology dimension it reports n-robust effect sizes
(probability of superiority A = P(USoc > BHPS)), location summaries, and the
STRAND log-rank statistic + label-permutation p-value, then applies a
pre-stated decision rule to recommend GO/NO-GO on Tier 2.

Decision rule (pre-stated, before inspecting results):
  - A_raw = probability of superiority on the raw contrast (baseline shift).
  - robust:    both matched controls keep A >= 0.70 AND log-rank rejects (p<0.05).
  - attenuated: matched A in [0.55, 0.70) but still rejects.
  - collapsed:  any matched A < 0.55 OR a matched contrast fails to reject.
  Tier-2 recommended unless H0 is 'collapsed' (horizon/size already explain it).

Usage:
    uv run python trajectory_tda/scripts/run_strand_attribution_probe.py
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - used only for a fixed, trusted `git rev-parse`
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from trajectory_tda.discovery.strand_comparison import (
    finite_lifetimes,
    strand_pvalue,
)

WORKTREE = Path(__file__).resolve().parents[2]
# PROJ_ROOT is the main checkout holding the gitignored frozen-diagram caches
# (two-path rule); overridable via TDL_PROJ_ROOT for portability across machines.
PROJ_ROOT = Path(os.environ.get("TDL_PROJ_ROOT", "C:/Users/steph/TDL"))
CACHE = PROJ_ROOT / "results/trajectory_tda_integration/stage1/cache"
OUTPUT_DATE = "2026-06-17"
OUTPUT_PATH = WORKTREE / f"results/trajectory_tda_strand/attribution/strand_attribution_probe_{OUTPUT_DATE}.json"

SEED = 42
B_STRAND = 1000

USOC_CACHE = CACHE / "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz"
BHPS_VARIANTS = {
    "raw": CACHE / "null_diagrams_bhps_frozen_B1000_L5000_seed42_2026-05-28.npz",
    "length_matched": CACHE / "null_diagrams_bhps_length_matched_truncate_frozen_B1000_L5000_seed42_2026-05-30.npz",
    "non_overlap": CACHE / "null_diagrams_bhps_nonoverlap_frozen_B1000_L5000_seed42_2026-06-09.npz",
}
VARIANT_CONTROLS = {
    "raw": "none (baseline)",
    "length_matched": "trajectory observation horizon (truncate to USoc)",
    "non_overlap": "BHPS sample size / wave overlap",
}


def _obs_lifetimes(npz_path: Path, dim_key: str) -> NDArray[np.float64]:
    """Finite observed persistence lifetimes for one diagram dimension.

    Args:
        npz_path: Path to a frozen diagram NPZ cache.
        dim_key: Array key inside the NPZ (e.g. ``obs_h0_diagram``).

    Returns:
        1-D array of finite persistence lifetimes (p = d - b).
    """
    with np.load(npz_path, allow_pickle=True) as data:
        dgm = np.asarray(data[dim_key], dtype=np.float64)
    return finite_lifetimes(dgm)


def probability_of_superiority(x: NDArray[np.float64], y: NDArray[np.float64]) -> float:
    """Common-language effect size A = P(X > Y) + 0.5 P(X = Y).

    Rank-based (O(n log n)); A=0.5 means no shift, A->1 means X stochastically
    dominates Y. Equals the Mann-Whitney U statistic divided by n_x * n_y.
    """
    n_x = len(x)
    n_y = len(y)
    if n_x == 0 or n_y == 0:
        return float("nan")
    pooled = np.concatenate([x, y])
    ranks = stats.rankdata(pooled)
    r_x = float(np.sum(ranks[:n_x]))
    u_x = r_x - n_x * (n_x + 1) / 2.0
    return float(u_x / (n_x * n_y))


def _classify(a_raw: float, a_matched: float, rejects: bool) -> str:
    """Per-control attribution verdict from the pre-stated rule.

    Args:
        a_raw: Probability of superiority on the raw (uncontrolled) contrast;
            retained for context/symmetry with the decision rule.
        a_matched: Probability of superiority on the matched-control contrast.
        rejects: Whether the STRAND log-rank test rejects at alpha=0.05.

    Returns:
        One of ``"robust"``, ``"attenuated"``, or ``"collapsed"``.
    """
    if a_matched < 0.55 or not rejects:
        return "collapsed"
    if a_matched >= 0.70:
        return "robust"
    return "attenuated"


def _git_head() -> str:
    """Return the current git HEAD SHA, or ``"unknown"`` if unavailable."""
    try:
        # Fixed argv, no shell, no user input -> the Bandit subprocess warnings
        # (B603/B607) are reviewed false positives for this provenance call.
        out = subprocess.run(  # nosec B603 B607
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(WORKTREE),
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def main() -> None:
    """Run the Tier-1 reuse-path attribution probe and write the result JSON.

    For each BHPS control variant and homology dimension, computes the
    probability-of-superiority effect size and STRAND log-rank p-value against
    USoc, applies the pre-stated robust/attenuated/collapsed rule, and records a
    GO/NO-GO recommendation for the Tier-2 study. No new persistent homology.
    """
    t0 = time.time()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_PATH.exists():
        raise SystemExit(f"Refusing to overwrite existing result: {OUTPUT_PATH}")

    print("=" * 70)
    print("Tier-1 STRAND attribution probe (reuse-path; no new PH)")
    print("=" * 70)

    usoc = {d: _obs_lifetimes(USOC_CACHE, f"obs_{d}_diagram") for d in ("h0", "h1")}

    contrasts: dict[str, Any] = {}
    for variant, path in BHPS_VARIANTS.items():
        contrasts[variant] = {"control": VARIANT_CONTROLS[variant], "dims": {}}
        for dim in ("h0", "h1"):
            bhps = _obs_lifetimes(path, f"obs_{dim}_diagram")
            us = usoc[dim]
            a = probability_of_superiority(us, bhps)
            res = strand_pvalue(us, bhps, B=B_STRAND, seed=SEED, two_sided=True)
            rejects = res["pvalue"] < 0.05
            cell = {
                "n_usoc": len(us),
                "n_bhps": len(bhps),
                "median_usoc": float(np.median(us)),
                "median_bhps": float(np.median(bhps)),
                "mean_usoc": float(np.mean(us)),
                "mean_bhps": float(np.mean(bhps)),
                "prob_superiority_usoc_gt_bhps": a,
                "logrank_stat": res["observed_stat"],
                "logrank_p": res["pvalue"],
                "rejects": rejects,
            }
            contrasts[variant]["dims"][dim] = cell
            print(
                f"  [{variant:14s} {dim}] A(USoc>BHPS)={a:.3f}  "
                f"med {cell['median_usoc']:.2f} vs {cell['median_bhps']:.2f}  "
                f"logrank p={res['pvalue']:.4f}"
            )

    # Apply the pre-stated decision rule per dimension.
    decision: dict[str, Any] = {}
    for dim in ("h0", "h1"):
        a_raw = contrasts["raw"]["dims"][dim]["prob_superiority_usoc_gt_bhps"]
        per_control = {}
        for variant in ("length_matched", "non_overlap"):
            cell = contrasts[variant]["dims"][dim]
            per_control[variant] = _classify(a_raw, cell["prob_superiority_usoc_gt_bhps"], cell["rejects"])
        verdicts = set(per_control.values())
        if "collapsed" in verdicts:
            overall = "collapsed"
        elif verdicts == {"robust"}:
            overall = "robust"
        else:
            overall = "attenuated"
        decision[dim] = {
            "a_raw": a_raw,
            "per_control": per_control,
            "overall": overall,
        }

    h0v = decision["h0"]["overall"]
    tier2 = h0v != "collapsed"
    decision["tier2_recommended"] = tier2
    decision["rationale"] = f"H0 shift is '{h0v}' under horizon- and size-matching. " + (
        "Horizon and BHPS-size are not the (sole) driver; the remaining "
        "USoc-scale / landmark-fraction confound is worth resolving -> Tier 2 "
        "(USoc-downsample control + matched-B power) is justified."
        if tier2
        else "Horizon/size matching removes the shift -> it is a confound artifact; PARK STRAND and skip Tier 2."
    )

    payload = {
        "schema_version": "strand-attribution-probe/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": "T-STRAND-1 Tier-1 attribution probe (reuse-path)",
        "git_head": _git_head(),
        "inputs": {
            "usoc_cache": str(USOC_CACHE),
            "bhps_variants": {k: str(v) for k, v in BHPS_VARIANTS.items()},
        },
        "params": {
            "B": B_STRAND,
            "seed": SEED,
            "effect_size": "probability_of_superiority A = P(USoc>BHPS)",
            "decision_rule": (
                "robust: both matched A>=0.70 and log-rank rejects; "
                "attenuated: A in [0.55,0.70) and rejects; "
                "collapsed: any matched A<0.55 or no rejection. "
                "Tier-2 recommended unless H0 collapsed."
            ),
            "no_new_persistent_homology": True,
        },
        "contrasts": contrasts,
        "decision": decision,
        "wall_time_seconds": round(time.time() - t0, 1),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print("\n-- decision --")
    for dim in ("h0", "h1"):
        print(
            f"  {dim}: a_raw={decision[dim]['a_raw']:.3f} -> {decision[dim]['overall']}"
            f"  ({decision[dim]['per_control']})"
        )
    print(f"\nTIER 2 RECOMMENDED: {tier2}")
    print(f"  {decision['rationale']}")
    print(f"\nOutput: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
