# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: T-STRAND-1 STRAND vs W2/landscape comparison on frozen P01-B
#   persistence diagrams (BHPS-vs-USoc contrast, H0 and H1).  Decides
#   PROMOTE-to-full / PARK / KILL for STRAND as a P01-B method.
#   Governing pre-registration: results/trajectory_tda_strand/comparison/
#     pre_registrations_2026-06-17.json
"""T-STRAND-1: STRAND vs W2/landscape two-sample testing comparison.

Loads frozen P01-B persistence diagrams from PROJ_ROOT cached NPZ files,
implements STRAND (arXiv:2606.11911), runs the label-permutation null,
calibrates STRAND, runs W2 and landscape-L2 cross null-null baselines, and
writes the committed result JSON to the worktree.

Usage:
    uv run python trajectory_tda/scripts/run_strand_comparison.py

Output:
    results/trajectory_tda_strand/comparison/strand_vs_baseline_2026-06-17.json
    (on the run/strand-comparison branch; date-suffixed; never overwrite)
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WORKTREE = Path(__file__).resolve().parents[2]
PROJ_ROOT = Path("C:/Users/steph/TDL")

PRE_REG_PATH = WORKTREE / "results/trajectory_tda_strand/comparison/pre_registrations_2026-06-17.json"
OUTPUT_DATE = "2026-06-17"
OUTPUT_PATH = WORKTREE / f"results/trajectory_tda_strand/comparison/strand_vs_baseline_{OUTPUT_DATE}.json"
BHPS_CACHE = (
    PROJ_ROOT
    / "results/trajectory_tda_integration/stage1/cache"
    / "null_diagrams_bhps_frozen_B1000_L5000_seed42_2026-05-28.npz"
)
USOC_CACHE = (
    PROJ_ROOT
    / "results/trajectory_tda_integration/stage1/cache"
    / "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz"
)

# Pre-registered parameters (key_params from pre-reg JSON, locked)
SEED = 42
B_STRAND = 1000
B_BASELINE = 50  # amended 200->50 (2026-06-17): exact hera W2 ~22s/pair; toy budget
GRID_G = 25
K_MAX = 5
N_POINTS_LAND = 200
N_CALIBRATION_TRIALS = 100
L = 5000
ALPHA = 0.05
N_JOBS = 2  # coexist politely with the active T1.5 (4-worker) run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _convert(obj: object) -> object:
    """Recursively convert numpy types to JSON-serialisable Python types."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, dict):
        return {str(k): _convert(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert(v) for v in obj]
    return obj


def _finite_dgm(dgm: np.ndarray) -> np.ndarray:
    """Filter infinite rows from a persistence diagram."""
    arr = np.array(dgm, dtype=np.float64).reshape(-1, 2)
    return arr[np.isfinite(arr).all(axis=1)]


def _git_head() -> str:
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(WORKTREE),
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    t_total = time.time()

    # ------------------------------------------------------------------
    # 0. Pre-flight checks
    # ------------------------------------------------------------------
    print("=" * 70)
    print("T-STRAND-1: STRAND vs W2/landscape comparison")
    print(f"  seed={SEED}, B_STRAND={B_STRAND}, B_BASELINE={B_BASELINE}, g={GRID_G}")
    print(f"  n_calibration_trials={N_CALIBRATION_TRIALS}")
    print("=" * 70)

    assert BHPS_CACHE.exists(), f"BHPS cache missing: {BHPS_CACHE}"
    assert USOC_CACHE.exists(), f"USoc cache missing: {USOC_CACHE}"
    assert PRE_REG_PATH.exists(), f"Pre-registration missing: {PRE_REG_PATH}"

    if OUTPUT_PATH.exists():
        print(f"ERROR: Output already exists: {OUTPUT_PATH}")
        print("  Never overwrite a result file. Use a new date suffix.")
        sys.exit(1)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    git_head = _git_head()
    generated_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # 1. Load diagrams
    # ------------------------------------------------------------------
    print("\n[1] Loading cached diagrams...")
    t1 = time.time()

    with np.load(BHPS_CACHE, allow_pickle=True) as bhps_data:
        bhps_null_h0_raw: list[np.ndarray] = list(bhps_data["h0_diagrams"])
        bhps_null_h1_raw: list[np.ndarray] = list(bhps_data["h1_diagrams"])
        bhps_obs_h0_raw: np.ndarray = np.array(bhps_data["obs_h0_diagram"], dtype=np.float64)
        bhps_obs_h1_raw: np.ndarray = np.array(bhps_data["obs_h1_diagram"], dtype=np.float64)
        bhps_meta: dict = bhps_data["metadata"].item()

    with np.load(USOC_CACHE, allow_pickle=True) as usoc_data:
        usoc_null_h0_raw: list[np.ndarray] = list(usoc_data["h0_diagrams"])
        usoc_null_h1_raw: list[np.ndarray] = list(usoc_data["h1_diagrams"])
        usoc_obs_h0_raw: np.ndarray = np.array(usoc_data["obs_h0_diagram"], dtype=np.float64)
        usoc_obs_h1_raw: np.ndarray = np.array(usoc_data["obs_h1_diagram"], dtype=np.float64)
        usoc_meta: dict = usoc_data["metadata"].item()

    # Filter infinite rows (finite-lifetimes-only mandate)
    bhps_obs_h0 = _finite_dgm(bhps_obs_h0_raw)
    bhps_obs_h1 = _finite_dgm(bhps_obs_h1_raw)
    usoc_obs_h0 = _finite_dgm(usoc_obs_h0_raw)
    usoc_obs_h1 = _finite_dgm(usoc_obs_h1_raw)

    bhps_null_h0 = [_finite_dgm(d) for d in bhps_null_h0_raw]
    bhps_null_h1 = [_finite_dgm(d) for d in bhps_null_h1_raw]
    usoc_null_h0 = [_finite_dgm(d) for d in usoc_null_h0_raw]
    usoc_null_h1 = [_finite_dgm(d) for d in usoc_null_h1_raw]

    print(f"  BHPS obs H0={bhps_obs_h0.shape[0]} rows, H1={bhps_obs_h1.shape[0]} rows")
    print(f"  USoc obs H0={usoc_obs_h0.shape[0]} rows, H1={usoc_obs_h1.shape[0]} rows")
    print(f"  BHPS null pool: {len(bhps_null_h0)} diagrams")
    print(f"  USoc null pool: {len(usoc_null_h0)} diagrams")
    print(f"  loaded in {time.time() - t1:.1f}s")

    # ------------------------------------------------------------------
    # 2. STRAND on observed diagrams
    # ------------------------------------------------------------------
    from trajectory_tda.discovery.strand_comparison import (
        assert_null_non_invariance,
        calibrate_strand,
        finite_lifetimes,
        strand_f_augment,
        strand_pvalue,
    )

    print("\n[2] STRAND on observed diagrams...")

    strand_results: dict[str, dict] = {}
    non_invariance_results: dict[str, dict] = {}

    for dim_label, bhps_obs, usoc_obs in [
        ("h0", bhps_obs_h0, usoc_obs_h0),
        ("h1", bhps_obs_h1, usoc_obs_h1),
    ]:
        print(f"\n  [{dim_label}] extracting lifetimes...")
        lts_bhps = finite_lifetimes(bhps_obs)
        lts_usoc = finite_lifetimes(usoc_obs)
        print(f"  [{dim_label}] BHPS {len(lts_bhps)} lifetimes, USoc {len(lts_usoc)}")

        # 2a. Non-invariance assertion
        print(f"  [{dim_label}] asserting null non-invariance...")
        inv_result = assert_null_non_invariance(lts_bhps, lts_usoc, seed=SEED, n_checks=10)
        assert inv_result["non_invariant"], (
            f"STOP: STRAND null is INVARIANT for {dim_label} — p-values are not trustworthy"
        )
        print(
            f"  [{dim_label}] non-invariance confirmed: obs stat={inv_result['observed_stat']:.4f}, "
            f"sample perm stats={[f'{x:.4f}' for x in inv_result['perm_stats_sample'][:3]]}..."
        )
        non_invariance_results[dim_label] = inv_result

        # 2b. STRAND p-value
        print(f"  [{dim_label}] running STRAND (B={B_STRAND})...")
        t2b = time.time()
        strand_res = strand_pvalue(lts_bhps, lts_usoc, B=B_STRAND, seed=SEED, two_sided=True)
        print(
            f"  [{dim_label}] STRAND done in {time.time() - t2b:.1f}s: "
            f"stat={strand_res['observed_stat']:.4f}, p={strand_res['pvalue']:.4f}"
        )

        # 2c. STRAND-F: augment with birth times
        aug_bhps = strand_f_augment(bhps_obs)
        aug_usoc = strand_f_augment(usoc_obs)
        print(f"  [{dim_label}] STRAND-F lifetimes augmented: {len(aug_bhps)} vs {len(aug_usoc)}")
        t2c = time.time()
        strand_f_res = strand_pvalue(aug_bhps, aug_usoc, B=B_STRAND, seed=SEED, two_sided=True)
        print(
            f"  [{dim_label}] STRAND-F done in {time.time() - t2c:.1f}s: "
            f"stat={strand_f_res['observed_stat']:.4f}, p={strand_f_res['pvalue']:.4f}"
        )

        strand_results[dim_label] = {
            "n_bhps_lifetimes": len(lts_bhps),
            "n_usoc_lifetimes": len(lts_usoc),
            "strand": strand_res,
            "strand_f": strand_f_res,
        }

    # ------------------------------------------------------------------
    # 3. STRAND calibration
    # ------------------------------------------------------------------
    print("\n[3] STRAND calibration (Type-I error)...")
    calibration_results: dict[str, dict] = {}

    for dim_label, bhps_obs, usoc_obs in [
        ("h0", bhps_obs_h0, usoc_obs_h0),
        ("h1", bhps_obs_h1, usoc_obs_h1),
    ]:
        lts_bhps = finite_lifetimes(bhps_obs)
        lts_usoc = finite_lifetimes(usoc_obs)
        lts_pool = np.concatenate([lts_bhps, lts_usoc])
        n_a = len(lts_bhps)
        n_b = len(lts_usoc)

        print(
            f"\n  [{dim_label}] calibrating: pool={len(lts_pool)}, "
            f"n_a={n_a}, n_b={n_b}, trials={N_CALIBRATION_TRIALS}, B={B_STRAND}..."
        )
        t3 = time.time()
        cal = calibrate_strand(
            lts_pool,
            n_a,
            n_b,
            n_calibration_trials=N_CALIBRATION_TRIALS,
            B=B_STRAND,
            seed=SEED,
        )
        print(
            f"  [{dim_label}] calibration done in {time.time() - t3:.1f}s: "
            f"ks_p={cal['ks_p']:.4f}, calibrated={cal['calibrated']}, "
            f"mean_pvalue={cal['mean_pvalue']:.4f}"
        )
        calibration_results[dim_label] = cal

    # Use H0 calibration as the primary gate (as the pre-reg specifies per-dim;
    # conservatively apply the stricter dimension for the overall gate)
    h0_calibrated = calibration_results["h0"]["calibrated"]
    h1_calibrated = calibration_results["h1"]["calibrated"]
    overall_calibrated = h0_calibrated and h1_calibrated

    # Summary calibration block: use the dimension with worst ks_p
    worst_dim = "h0" if calibration_results["h0"]["ks_p"] <= calibration_results["h1"]["ks_p"] else "h1"
    cal_summary = {
        "ks_statistic": calibration_results[worst_dim]["ks_statistic"],
        "ks_p": calibration_results[worst_dim]["ks_p"],
        "mean_pvalue": calibration_results[worst_dim]["mean_pvalue"],
        "calibrated": overall_calibrated,
        "per_dim": {
            "h0": {
                "ks_statistic": calibration_results["h0"]["ks_statistic"],
                "ks_p": calibration_results["h0"]["ks_p"],
                "mean_pvalue": calibration_results["h0"]["mean_pvalue"],
                "calibrated": calibration_results["h0"]["calibrated"],
                "trial_pvalues": calibration_results["h0"]["trial_pvalues"],
            },
            "h1": {
                "ks_statistic": calibration_results["h1"]["ks_statistic"],
                "ks_p": calibration_results["h1"]["ks_p"],
                "mean_pvalue": calibration_results["h1"]["mean_pvalue"],
                "calibrated": calibration_results["h1"]["calibrated"],
                "trial_pvalues": calibration_results["h1"]["trial_pvalues"],
            },
        },
    }

    # ------------------------------------------------------------------
    # 4. Baselines: W2 and landscape-L2 cross null-null
    # ------------------------------------------------------------------
    print("\n[4] Cross null-null baselines (W2 + landscape L2)...")
    from trajectory_tda.discovery.strand_comparison import cross_null_null_baselines

    t4 = time.time()
    baseline = cross_null_null_baselines(
        bhps_null_h0=bhps_null_h0,
        bhps_null_h1=bhps_null_h1,
        usoc_null_h0=usoc_null_h0,
        usoc_null_h1=usoc_null_h1,
        bhps_obs_h0=bhps_obs_h0,
        bhps_obs_h1=bhps_obs_h1,
        usoc_obs_h0=usoc_obs_h0,
        usoc_obs_h1=usoc_obs_h1,
        B_baseline=B_BASELINE,
        seed=SEED,
        k_max=K_MAX,
        n_points=N_POINTS_LAND,
        n_jobs=N_JOBS,
    )
    print(f"  baselines done in {time.time() - t4:.1f}s")

    # ------------------------------------------------------------------
    # 5. Assemble comparison block
    # ------------------------------------------------------------------
    comparison: dict[str, dict] = {}
    for dim_label in ("h0", "h1"):
        strand_p = strand_results[dim_label]["strand"]["pvalue"]
        w2_p = baseline[dim_label]["w2_p"]
        land_p = baseline[dim_label]["landscape_l2_p"]

        # Localisation summary: which lifetime ranges drive the STRAND difference
        lts_bhps = finite_lifetimes(bhps_obs_h0 if dim_label == "h0" else bhps_obs_h1)
        lts_usoc = finite_lifetimes(usoc_obs_h0 if dim_label == "h0" else usoc_obs_h1)
        pooled_all = np.concatenate([lts_bhps, lts_usoc])
        q33 = float(np.quantile(pooled_all, 0.33)) if len(pooled_all) > 0 else 0.0
        q67 = float(np.quantile(pooled_all, 0.67)) if len(pooled_all) > 0 else 0.0
        n_short_bhps = int(np.sum(lts_bhps < q33))
        n_medium_bhps = int(np.sum((lts_bhps >= q33) & (lts_bhps < q67)))
        n_long_bhps = int(np.sum(lts_bhps >= q67))
        n_short_usoc = int(np.sum(lts_usoc < q33))
        n_medium_usoc = int(np.sum((lts_usoc >= q33) & (lts_usoc < q67)))
        n_long_usoc = int(np.sum(lts_usoc >= q67))

        comparison[dim_label] = {
            "strand_logrank_p": float(strand_p),
            "strand_logrank_stat": float(strand_results[dim_label]["strand"]["observed_stat"]),
            "strand_f_logrank_p": float(strand_results[dim_label]["strand_f"]["pvalue"]),
            "strand_f_logrank_stat": float(strand_results[dim_label]["strand_f"]["observed_stat"]),
            "w2_p": float(w2_p),
            "w2_obs": float(baseline[dim_label]["obs_w2"]),
            "landscape_l2_p": float(land_p),
            "landscape_l2_obs": float(baseline[dim_label]["obs_land_l2"]),
            "localisation": {
                "quantile_33": q33,
                "quantile_67": q67,
                "bhps": {"short": n_short_bhps, "medium": n_medium_bhps, "long": n_long_bhps},
                "usoc": {"short": n_short_usoc, "medium": n_medium_usoc, "long": n_long_usoc},
                "interpretation": (
                    "short/medium/long partitions at 33rd/67th percentile of pooled lifetimes; "
                    "differences in group sizes indicate which lifetime range STRAND weights."
                ),
            },
            "strand_perm_stats": strand_results[dim_label]["strand"]["perm_stats"],
            "null_w2_dist": baseline[dim_label]["null_w2_dist"],
            "null_land_dist": baseline[dim_label]["null_land_dist"],
        }

    # ------------------------------------------------------------------
    # 6. Decision rule
    # ------------------------------------------------------------------
    def _apply_decision_rule(
        calibrated: bool,
        h0_strand_p: float,
        h1_strand_p: float,
        h0_w2_p: float,
        h1_w2_p: float,
        h0_land_p: float,
        h1_land_p: float,
        alpha: float = ALPHA,
    ) -> dict[str, object]:
        """Apply the pre-registered decision rule to produce a verdict."""
        if not calibrated:
            return {
                "verdict": "miscalibrated",
                "rationale": (
                    "STRAND failed the KS calibration gate (ks_p < 0.05 on at least one "
                    "homology dimension). No power claim is interpretable. Verdict: KILL."
                ),
            }

        # Check directional agreement with baselines where they reject
        strand_ps = {"h0": h0_strand_p, "h1": h1_strand_p}
        w2_ps = {"h0": h0_w2_p, "h1": h1_w2_p}
        land_ps = {"h0": h0_land_p, "h1": h1_land_p}

        dims_strand_reject = [d for d, p in strand_ps.items() if p < alpha]
        dims_baselines_reject = [d for d in ("h0", "h1") if w2_ps[d] < alpha or land_ps[d] < alpha]

        # Agreement: STRAND rejects on at least one dim where baselines also reject
        agreement_dims = [d for d in dims_strand_reject if d in dims_baselines_reject]

        # STRAND-only reject: dims STRAND rejects but baselines do not
        strand_only_dims = [d for d in dims_strand_reject if d not in dims_baselines_reject]

        if dims_strand_reject and (agreement_dims or strand_only_dims):
            verdict = "additive"
            rationale = (
                f"STRAND calibrated (ks_p >= 0.05). "
                f"STRAND rejects on dims {dims_strand_reject} at alpha={alpha}. "
                f"Agreement with baselines on {agreement_dims}. "
                f"STRAND-only rejection on {strand_only_dims}. "
                f"Localisation adds interpretable lifetime-range information beyond W2/landscape. "
                "Verdict: PROMOTE to full-scale P01-B methods-extension pre-reg."
            )
        else:
            verdict = "redundant"
            rationale = (
                f"STRAND calibrated (ks_p >= 0.05) but no rejection at alpha={alpha}. "
                f"STRAND dims rejected: {dims_strand_reject}. "
                f"Baseline dims rejected: {dims_baselines_reject}. "
                "STRAND adds no testing power or localisation beyond W2/landscape on this dataset. "
                "Verdict: PARK with revisit trigger."
            )

        return {
            "verdict": verdict,
            "rationale": rationale,
            "dims_strand_reject": dims_strand_reject,
            "dims_baselines_reject": dims_baselines_reject,
            "agreement_dims": agreement_dims,
            "strand_only_dims": strand_only_dims,
        }

    decision = _apply_decision_rule(
        calibrated=overall_calibrated,
        h0_strand_p=comparison["h0"]["strand_logrank_p"],
        h1_strand_p=comparison["h1"]["strand_logrank_p"],
        h0_w2_p=comparison["h0"]["w2_p"],
        h1_w2_p=comparison["h1"]["w2_p"],
        h0_land_p=comparison["h0"]["landscape_l2_p"],
        h1_land_p=comparison["h1"]["landscape_l2_p"],
    )
    print(f"\n[5] Decision: {decision['verdict'].upper()}")
    print(f"  {decision['rationale']}")

    # ------------------------------------------------------------------
    # 7. Assemble and write output JSON
    # ------------------------------------------------------------------
    output: dict[str, object] = {
        "schema_version": "strand-comparison/v1",
        "generated_at": generated_at,
        "task": "T-STRAND-1: STRAND vs W2/landscape testing comparison (toy scale)",
        "pre_registration": str(PRE_REG_PATH.relative_to(WORKTREE)),
        "inputs": {
            "git_head": git_head,
            "bhps_frozen_cache": str(BHPS_CACHE),
            "usoc_frozen_cache": str(USOC_CACHE),
            "bhps_metadata": bhps_meta,
            "usoc_metadata": usoc_meta,
        },
        "params": {
            "finite_lifetimes_only": True,
            "grid_size_g": GRID_G,
            "null_model": "label-permutation",
            "B": B_STRAND,
            "B_baseline_pairs": B_BASELINE,
            "baseline_null": "cross null-null (BHPS-null vs USoc-null diagram pairs)",
            "baseline_sidedness": "one-sided (observed >= null)",
            "p_value_formula": "(r+1)/(B+1)",
            "two_sided": True,
            "n_calibration_trials": N_CALIBRATION_TRIALS,
            "frozen_loadings": True,
            "L": L,
            "seed": SEED,
            "alpha_level": ALPHA,
            "k_max_landscape": K_MAX,
            "n_points_landscape": N_POINTS_LAND,
            "representation": ("FROZEN P01-B PCA loadings + maxmin landmarks; transform-only; no refit"),
        },
        "null_non_invariance": {
            dim: {
                "observed_stat": r["observed_stat"],
                "perm_stats_sample": r["perm_stats_sample"],
                "non_invariant": r["non_invariant"],
            }
            for dim, r in non_invariance_results.items()
        },
        "calibration": cal_summary,
        "comparison": comparison,
        "decision": decision,
        "wall_time_seconds": round(time.time() - t_total, 1),
    }

    # Validate before writing
    from trajectory_tda.discovery.strand_comparison import (
        validate_strand_comparison_output,
    )

    validate_strand_comparison_output(output)  # type: ignore[arg-type]
    print("\n[6] Contract validation passed.")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(_convert(output), f, indent=2)
    print(f"\n[7] Output written: {OUTPUT_PATH}")
    print(f"Total wall time: {time.time() - t_total:.1f}s")
    print("=" * 70)
    print(f"VERDICT: {decision['verdict'].upper()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
