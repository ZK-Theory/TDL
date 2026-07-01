# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: T1.28 per-subgroup stratified Markov-1 W2 recompute for USoc + BHPS.
#   Runs the canonical headline (subgroup observed PD vs own Markov-1 null) for
#   each demographic subgroup under frozen full-sample PCA-20 loadings.
#   Checkpoints per subgroup (resumable). Supports single-subgroup dispatch.
"""T1.28 stratified W2 recompute — per-subgroup Markov-1 W2 headline.

Usage examples::

    # Show subgroup plan (n per subgroup, no compute):
    uv run --env-file .env python trajectory_tda/scripts/run_t128_stratified_w2.py --plan

    # Run a single subgroup (for separate task dispatch):
    uv run --env-file .env python trajectory_tda/scripts/run_t128_stratified_w2.py \\
        --dataset bhps --stratifier cohort --label 1930s

    # Run all subgroups for one dataset (sequential, with per-subgroup checkpoints):
    uv run --env-file .env python trajectory_tda/scripts/run_t128_stratified_w2.py \\
        --dataset bhps --wall-time-hours 12

    # Run all subgroups, both datasets:
    uv run --env-file .env python trajectory_tda/scripts/run_t128_stratified_w2.py

Outputs (per-subgroup checkpoints at PROJ_ROOT, gitignored)::

    results/panel_methodology/fdr/subgroup_checkpoints/
        <dataset>_<stratifier>_<label>_B1000_seed42.json

Assembly (separate step via run_t128_assemble.py) collects completed checkpoints
into the committed stratified_w2_recompute_<date>.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("t128_stratified_w2")

# ── Two-path output roots (APM two-path rule) ─────────────────────────────────

PROJ_ROOT = Path("C:/Users/steph/TDL")
WORKTREE = Path(__file__).resolve().parent.parent.parent  # repo root

# ── Checkpoint directories ────────────────────────────────────────────────────

USOC_CKPT = PROJ_ROOT / "results/trajectory_tda_integration"
BHPS_CKPT = PROJ_ROOT / "results/trajectory_tda_bhps"

SUBGROUP_CKPT_DIR = PROJ_ROOT / "results/panel_methodology/fdr/subgroup_checkpoints"

# ── Pre-registered parameters (locked 2026-06-13 + amendments 2026-06-27/28) ──

B_DEFAULT = 1000
SEED = 42
MARKOV_ORDER = 1
# N_JOBS reverted 12→4 (2026-07-01): the 4→12 upgrade assumed the perm phase
# was CPU-core-bound (safe because it isn't AGG's null-null cost-matrix path).
# A live test flight + isolated benchmark falsified that: per-task latency at
# n_jobs=12 was ~6.4x the solo-call cost vs ~2.4x at n_jobs=4 (reconstructed
# from batch-log elapsed*n_jobs/tasks_done), with system CPU at only ~26% and
# 4.3GB/32GB RAM free — the signature of memory-bandwidth/cache contention
# scaling worse with worker count, not a core-count ceiling. 4 is the
# known-good throughput; see the giotto-ph/giotto-tda feasibility spike for
# the actual fix under investigation.
N_JOBS = 4
N_JOBS_AGG = 12  # AGG phase only — infrastructure, not a statistical parameter
K_MAX = 5
N_POINTS = 200
L_DEFAULT = 5000
ALPHA_LEVEL = 0.05
P_FORMULA = "(r+1)/(B+1)"

# ── Subgroup plan (USoc 12, BHPS 11) ─────────────────────────────────────────
# Pre-registered via 2026-06-27 amendment (nssec 3-class, cohort 7/6 decades).
# Source keys match extract_covariates output columns.

USOC_SUBGROUPS: list[tuple[str, str]] = [
    ("gender", "Female"),
    ("gender", "Male"),
    ("nssec", "Intermediate"),
    ("nssec", "Professional/Managerial"),
    ("nssec", "Routine/Manual"),
    ("cohort", "1930s"),
    ("cohort", "1940s"),
    ("cohort", "1950s"),
    ("cohort", "1960s"),
    ("cohort", "1970s"),
    ("cohort", "1980s"),
    ("cohort", "1990s"),
]

BHPS_SUBGROUPS: list[tuple[str, str]] = [
    ("gender", "Female"),
    ("gender", "Male"),
    ("nssec", "Intermediate"),
    ("nssec", "Professional/Managerial"),
    ("nssec", "Routine/Manual"),
    ("cohort", "1930s"),
    ("cohort", "1940s"),
    ("cohort", "1950s"),
    ("cohort", "1960s"),
    ("cohort", "1970s"),
    ("cohort", "1980s"),
    # 1990s excluded from BHPS: n=0 (panel ended 2009; 2026-06-28 amendment)
]

DATASET_SUBGROUPS: dict[str, list[tuple[str, str]]] = {
    "usoc": USOC_SUBGROUPS,
    "bhps": BHPS_SUBGROUPS,
}

DATASET_CKPT: dict[str, Path] = {
    "usoc": USOC_CKPT,
    "bhps": BHPS_CKPT,
}


# ── Covariate loading ─────────────────────────────────────────────────────────


def _load_dataset_covariates(
    dataset: str,
    trajectories: list[list[str]],
    ckpt_dir: Path,
) -> dict[str, NDArray[Any]]:
    """Return stratification arrays aligned to embedding row indices.

    Returns dict with keys:
        ``gender``: str array, "Female"/"Male"/None
        ``nssec``:  str array, 3-class parental NS-SEC label / None
        ``cohort``: str array, decade label "1930s"…"1990s" / None
    """

    import pandas as pd

    from trajectory_tda.data.covariate_extractor import extract_covariates

    n = len(trajectories)

    # ── pidp and birth_year from 01_trajectories.json metadata ───────────────
    meta_path = ckpt_dir / "01_trajectories.json"
    with open(meta_path) as f:
        meta = json.load(f)["metadata"]

    pidp_raw: dict[str, Any] = meta.get("pidp", {})
    birth_year_raw: dict[str, Any] = meta.get("birth_year", {})

    pidps = np.array([int(pidp_raw[str(i)]) for i in range(n)], dtype=np.int64)

    birth_years = np.array(
        [float(v) if (v := birth_year_raw.get(str(i))) is not None else np.nan for i in range(n)],
        dtype=np.float64,
    )
    cohort_arr = np.array(
        [f"{int(by // 10) * 10}s" if np.isfinite(by) else None for by in birth_years],
        dtype=object,
    )

    # ── sex and parental NS-SEC from covariate_extractor ─────────────────────
    data_dir_env = os.environ.get("TRAJECTORY_TDA_DATA_DIR")
    if data_dir_env:
        data_dir = Path(data_dir_env)
    else:
        from importlib.resources import files

        data_dir = Path(str(files("trajectory_tda").joinpath("data")))

    logger.info("[%s] extracting covariates for %d pidps from %s", dataset, n, data_dir)
    covs: pd.DataFrame = extract_covariates(data_dir, pidps)
    covs = covs.drop_duplicates(subset="pidp").set_index("pidp")

    sex_arr = np.array(
        [covs.loc[p, "sex"] if p in covs.index else None for p in pidps],
        dtype=object,
    )
    nssec_arr = np.array(
        [covs.loc[p, "parental_nssec3"] if p in covs.index else None for p in pidps],
        dtype=object,
    )

    # Coverage report
    n_sex = int(np.sum(sex_arr != None))  # noqa: E711
    n_nssec = int(np.sum(nssec_arr != None))  # noqa: E711
    n_cohort = int(np.sum(cohort_arr != None))  # noqa: E711
    logger.info(
        "[%s] covariate coverage — gender: %d/%d  nssec: %d/%d  cohort: %d/%d",
        dataset,
        n_sex,
        n,
        n_nssec,
        n,
        n_cohort,
        n,
    )

    return {
        "gender": sex_arr,
        "nssec": nssec_arr,
        "cohort": cohort_arr,
    }


def _subgroup_indices(
    cov_arrays: dict[str, NDArray[Any]],
    stratifier: str,
    label: str,
) -> NDArray[np.intp]:
    """Return row indices where stratifier == label."""
    arr = cov_arrays[stratifier]
    return np.where(arr == label)[0]


# ── Frozen models ─────────────────────────────────────────────────────────────


def _build_frozen_models(
    trajectories: list[list[str]],
    embed_kwargs: dict[str, Any],
    dataset: str,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """Re-run ngram_embed on the full trajectory set to get frozen PCA/scaler.

    Returns (full_embeddings, frozen_models_dict) where frozen_models_dict
    has keys ``scaler`` and ``reducer`` — passed to run_headline_from_embeddings
    so null permutations use transform-only (no refit).
    """
    from trajectory_tda.embedding.ngram_embed import ngram_embed

    logger.info(
        "[%s] re-embedding %d trajectories to capture frozen models ...",
        dataset,
        len(trajectories),
    )
    t0 = time.perf_counter()
    full_embeddings, info = ngram_embed(trajectories, **embed_kwargs)
    elapsed = time.perf_counter() - t0
    logger.info(
        "[%s] frozen models ready in %.1fs — embedding shape %s",
        dataset,
        elapsed,
        full_embeddings.shape,
    )
    return full_embeddings, info["fitted_models"]


# ── Per-subgroup checkpoint I/O ───────────────────────────────────────────────


def _ckpt_path(dataset: str, stratifier: str, label: str, B: int) -> Path:
    safe_label = label.replace("/", "-").replace(" ", "_")
    return SUBGROUP_CKPT_DIR / f"{dataset}_{stratifier}_{safe_label}_B{B}_seed{SEED}.json"


def _load_ckpt(dataset: str, stratifier: str, label: str, B: int) -> dict[str, Any] | None:
    p = _ckpt_path(dataset, stratifier, label, B)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return None


def _save_ckpt(
    dataset: str,
    stratifier: str,
    label: str,
    B: int,
    result: dict[str, Any],
) -> Path:
    SUBGROUP_CKPT_DIR.mkdir(parents=True, exist_ok=True)
    p = _ckpt_path(dataset, stratifier, label, B)
    with open(p, "w") as f:
        json.dump(result, f, indent=2)
    logger.info("Checkpoint saved: %s", p)
    return p


# ── Single subgroup run ───────────────────────────────────────────────────────


def run_subgroup(
    dataset: str,
    stratifier: str,
    label: str,
    embeddings: NDArray[np.float64],
    trajectories: list[list[str]],
    embed_kwargs: dict[str, Any],
    cov_arrays: dict[str, NDArray[Any]],
    frozen_models: dict[str, Any],
    B: int = B_DEFAULT,
    force: bool = False,
    perms_only: bool = False,
) -> dict[str, Any]:
    """Run the Markov-1 W2 headline for one (dataset, stratifier, label) subgroup.

    Args:
        dataset: "usoc" or "bhps".
        stratifier: "gender", "nssec", or "cohort".
        label: Subgroup label, e.g. "Female", "1960s".
        embeddings: Full-sample embedding array (n_total, d).
        trajectories: Full-sample trajectory list (n_total,).
        embed_kwargs: Embedding parameters from checkpoint.
        cov_arrays: Dict of stratification arrays from _load_dataset_covariates.
        frozen_models: Fitted scaler+reducer from _build_frozen_models.
        B: Permutation count (pre-registered 1000).
        force: Re-run even if checkpoint exists.

    Returns:
        Per-subgroup result dict ready for JSON serialisation.
    """
    from trajectory_tda.scripts.stage1._battery_core import run_headline_from_embeddings

    tag = f"{dataset}/{stratifier}/{label}"

    # ── Check existing checkpoint ─────────────────────────────────────────────
    if not force:
        cached = _load_ckpt(dataset, stratifier, label, B)
        if cached is not None:
            logger.info("[%s] checkpoint exists — skipping", tag)
            return cached

    # ── Subgroup slice ────────────────────────────────────────────────────────
    indices = _subgroup_indices(cov_arrays, stratifier, label)
    n_sub = len(indices)
    if n_sub == 0:
        raise ValueError(f"[{tag}] No rows matched — check covariate coverage")

    actual_lm = min(L_DEFAULT, n_sub)
    logger.info(
        "[%s] n=%d  actual_landmarks=%d  B=%d  seed=%d",
        tag,
        n_sub,
        actual_lm,
        B,
        SEED,
    )

    sub_embeddings = embeddings[indices]
    sub_trajectories = [trajectories[int(i)] for i in indices]

    # ── Run headline ──────────────────────────────────────────────────────────
    phase_tag = f"t128_{dataset}_{stratifier}_{label.replace('/', '-').replace(' ', '_')}"
    t_start = time.perf_counter()

    result_dict, _null_results, _ph_obs = run_headline_from_embeddings(
        embeddings=sub_embeddings,
        trajectories=sub_trajectories,
        embed_kwargs=embed_kwargs,
        n_permutations=B,
        n_landmarks=actual_lm,
        k_max=K_MAX,
        n_points=N_POINTS,
        seed=SEED,
        label=tag,
        phase_tag=phase_tag,
        n_jobs=N_JOBS,
        n_jobs_agg=N_JOBS_AGG,
        markov_order=MARKOV_ORDER,
        frozen_models=frozen_models,
        perms_only=perms_only,
        null_do_cocycles=False,
    )

    if perms_only:
        elapsed = time.perf_counter() - t_start
        logger.info("[%s] perms-only done in %.1fs (%.2fh)", tag, elapsed, elapsed / 3600)
        return {}

    elapsed = time.perf_counter() - t_start
    logger.info("[%s] headline done in %.1fs (%.2fh)", tag, elapsed, elapsed / 3600)

    # ── Extract H0 primary metrics (pre-registered: W2 + landscape L2) ───────
    h0 = result_dict.get("h0", {})
    h1 = result_dict.get("h1", {})

    w2_p = float(h0.get("w2_pvalue", float("nan")))
    t_ratio = float(h0.get("t_ratio", float("nan")))
    bca_lo = h0.get("bca_ci_lower")
    bca_hi = h0.get("bca_ci_upper")
    bca_ci = [
        float(bca_lo) if bca_lo is not None else float("nan"),
        float(bca_hi) if bca_hi is not None else float("nan"),
    ]
    landscape_l2_p = float(h0.get("landscape_l2_pvalue", float("nan")))

    subgroup_result: dict[str, Any] = {
        "dataset": dataset,
        "stratifier": stratifier,
        "subgroup_id": label,
        "n": int(n_sub),
        "actual_landmarks": int(actual_lm),
        "t_ratio": t_ratio,
        "bca_ci": bca_ci,
        "w2_p": w2_p,
        "w2_rejects": bool(w2_p < ALPHA_LEVEL),
        "landscape_l2_p": landscape_l2_p,
        # Supplementary H1 (not in primary contract, stored for diagnostics)
        "h1_w2_p": float(h1.get("w2_pvalue", float("nan"))),
        "h1_t_ratio": float(h1.get("t_ratio", float("nan"))),
        "h1_landscape_l2_p": float(h1.get("landscape_l2_pvalue", float("nan"))),
        # Provenance
        "elapsed_s": round(elapsed, 1),
        "B": B,
        "seed": SEED,
        "markov_order": MARKOV_ORDER,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    _save_ckpt(dataset, stratifier, label, B, subgroup_result)
    return subgroup_result


# ── Plan reporting ────────────────────────────────────────────────────────────


def print_plan(
    dataset_filter: str | None,
    stratifier_filter: str | None,
    label_filter: str | None,
    embeddings_cache: dict[str, NDArray[np.float64]] | None = None,
    cov_cache: dict[str, dict[str, NDArray[Any]]] | None = None,
) -> None:
    """Print the subgroup plan (with approximate n if data is loaded)."""
    for ds, subgroups in DATASET_SUBGROUPS.items():
        if dataset_filter and ds != dataset_filter:
            continue
        print(f"\n{'=' * 60}")
        print(f"Dataset: {ds.upper()}")
        print(f"{'=' * 60}")
        for strat, lbl in subgroups:
            if stratifier_filter and strat != stratifier_filter:
                continue
            if label_filter and lbl != label_filter:
                continue
            ckpt = _load_ckpt(ds, strat, lbl, B_DEFAULT)
            status = "DONE" if ckpt is not None else "pending"
            n_str = ""
            if cov_cache and ds in cov_cache:
                idx = _subgroup_indices(cov_cache[ds], strat, lbl)
                n_str = f"  n={len(idx)}  L={min(L_DEFAULT, len(idx))}"
            print(f"  {strat:10s}  {lbl:25s}  [{status}]{n_str}")


# ── Main ──────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T1.28 stratified W2 recompute — per-subgroup Markov-1 W2 headline")
    parser.add_argument(
        "--dataset",
        choices=["usoc", "bhps", "all"],
        default="all",
        help="Dataset to run (default: all)",
    )
    parser.add_argument(
        "--stratifier",
        choices=["gender", "nssec", "cohort", "all"],
        default="all",
        help="Stratifier to run (default: all)",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Specific subgroup label, e.g. '1930s' or 'Female' (default: all labels)",
    )
    parser.add_argument(
        "--B",
        type=int,
        default=B_DEFAULT,
        help=f"Permutation count (default: {B_DEFAULT}; pre-registered)",
    )
    parser.add_argument(
        "--wall-time-hours",
        type=float,
        default=48.0,
        help="Soft wall-time limit in hours (exit gracefully when exceeded)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run subgroups even if a checkpoint exists",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Print the subgroup plan and checkpoint status, then exit",
    )
    parser.add_argument(
        "--perms-only",
        action="store_true",
        help="Run permutation phase only — write perm cache and stop before AGG",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    dataset_filter = None if args.dataset == "all" else args.dataset
    strat_filter = None if args.stratifier == "all" else args.stratifier

    if args.plan:
        # Quick plan print without loading data
        print_plan(dataset_filter, strat_filter, args.label)
        return

    wall_deadline = time.perf_counter() + args.wall_time_hours * 3600
    session_start = time.perf_counter()

    # ── Load checkpoints and covariates per dataset ───────────────────────────
    from trajectory_tda.scripts.run_wasserstein_battery import load_checkpoint

    datasets_to_run = [dataset_filter] if dataset_filter else list(DATASET_SUBGROUPS)

    for ds in datasets_to_run:
        ckpt_dir = DATASET_CKPT[ds]
        subgroups = [
            (strat, lbl)
            for strat, lbl in DATASET_SUBGROUPS[ds]
            if (strat_filter is None or strat == strat_filter) and (args.label is None or lbl == args.label)
        ]
        if not subgroups:
            logger.warning("[%s] no subgroups match filters — skipping", ds)
            continue

        logger.info("[%s] loading checkpoint from %s", ds, ckpt_dir)
        embeddings, trajectories, embed_kwargs = load_checkpoint(ckpt_dir)
        logger.info(
            "[%s] checkpoint loaded: %d trajectories, %d-D embeddings",
            ds,
            len(trajectories),
            embeddings.shape[1],
        )

        logger.info("[%s] loading covariates ...", ds)
        cov_arrays = _load_dataset_covariates(ds, trajectories, ckpt_dir)

        logger.info("[%s] building frozen models (full-sample ngram_embed) ...", ds)
        full_embeddings, frozen_models = _build_frozen_models(trajectories, embed_kwargs, ds)

        # ── Run each subgroup ─────────────────────────────────────────────────
        for strat, lbl in subgroups:
            if time.perf_counter() > wall_deadline:
                elapsed_h = (time.perf_counter() - session_start) / 3600
                logger.warning(
                    "Wall-time limit %.1fh reached after %.2fh — exiting gracefully. "
                    "Completed subgroups are checkpointed at %s.",
                    args.wall_time_hours,
                    elapsed_h,
                    SUBGROUP_CKPT_DIR,
                )
                return

            try:
                run_subgroup(
                    dataset=ds,
                    stratifier=strat,
                    label=lbl,
                    embeddings=full_embeddings,
                    trajectories=trajectories,
                    embed_kwargs=embed_kwargs,
                    cov_arrays=cov_arrays,
                    frozen_models=frozen_models,
                    B=args.B,
                    force=args.force,
                    perms_only=args.perms_only,
                )
            except Exception:
                logger.exception("[%s/%s/%s] FAILED — continuing to next subgroup", ds, strat, lbl)

    total_elapsed = (time.perf_counter() - session_start) / 3600
    logger.info("All targeted subgroups processed in %.2fh.", total_elapsed)


if __name__ == "__main__":
    main()
