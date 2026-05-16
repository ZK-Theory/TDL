# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.19 rerun — refit StandardScaler + PCA (svd_solver='full') + GMM from
#          raw trajectory features; build 10-year overlapping windows; predict per-window
#          regimes; compute escape outcomes for R2/R6 starters using good_regimes={1,4}.
#          Saves per-person window assignments JSON for downstream R regression.
#
# The v1 escape analysis is window-based: each person's jbstat sequence is sliced into
# overlapping 10-year windows (step=5). A person is a "disadvantaged starter" if their
# FIRST window falls in GMM regime {2,6}. "Escape" = any subsequent window in regime {1,4}.
#
# Note: "escape" is defined as reaching good_regimes={1,4} (stable employment), NOT
# merely leaving {2,6}. This matches the original run_priority2.py (GOOD_REGIMES={1,4}).
#
# PCA uses svd_solver='full' (exact LAPACK SVD) for deterministic results independent
# of sklearn version or random state. The original 02_scaler.joblib and 02_pca.joblib
# used PCA(n_components=20, random_state=42) under sklearn 1.3.2 which is incompatible
# with sklearn 1.8.0's randomized SVD. Full SVD gives the true optimal components.
#
# GMM is refit on the sign-corrected refit embeddings (not orig_embeddings.npy) so
# that windows embedded through the same scaler+PCA pipeline land in the correct GMM space.
# Sign-correction against orig_embeddings.npy ensures label_map consistency.
#
# Run from worktree root:
#   uv run --env-file .env python trajectory_tda/analysis/panel/build_window_assignments.py

from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJ_ROOT  = Path("C:/Users/steph/TDL")
CP_DIR     = PROJ_ROOT / "results/trajectory_tda_integration"
OUT_DIR    = PROJ_ROOT / "results/trajectory_tda_priority2"
XWAVEDAT   = PROJ_ROOT / "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab"
TODAY      = date.today().strftime("%Y-%m-%d")
OUT_PATH   = OUT_DIR / f"window_escape_assignments_{TODAY}.json"

N_COMPONENTS   = 7
RANDOM_STATE   = 42
N_INIT         = 5
WINDOW_YEARS   = 10
WINDOW_STEP    = 5
DISADV_ORIG    = {2, 6}
GOOD_ORIG      = {1, 4}   # escape = reaching stable employment (R1) or regular employment (R4)

# Expected reference values from p2_5_age_stratified.json
REF_N_STARTERS = 7453
REF_RATE       = 0.05581644975177781


def load_birth_years(pidps: list[int]) -> dict[int, int | None]:
    """Load birth years from xwavedat, keyed by pidp."""
    logger.info("Loading birth years from xwavedat...")
    import csv
    birth_years: dict[int, int | None] = {}
    with open(XWAVEDAT, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                pidp = int(row["pidp"])
                by_raw = row.get("birthy", "")
                by = int(by_raw) if by_raw.strip().lstrip("-").isdigit() else None
                if by is not None and (by <= 1900 or by > 2005):
                    by = None
                birth_years[pidp] = by
            except (ValueError, KeyError):
                continue
    logger.info(f"Loaded birth years for {len(birth_years):,} individuals")
    return birth_years


def build_label_map(
    new_labels: np.ndarray, orig_labels: np.ndarray, n_components: int
) -> dict[int, int]:
    """Map new GMM label indices to original label indices by majority vote."""
    label_map: dict[int, int] = {}
    for k in range(n_components):
        mask = new_labels == k
        if mask.sum() == 0:
            label_map[k] = k
            continue
        orig_subset = orig_labels[mask]
        counts = np.bincount(orig_subset, minlength=n_components)
        label_map[k] = int(counts.argmax())
    return label_map


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Step 1: Load original labels and embeddings for reference
    # ------------------------------------------------------------------
    logger.info("Loading original labels from 05_analysis.json...")
    with open(CP_DIR / "05_analysis.json") as f:
        analysis = json.load(f)
    orig_labels = np.array(analysis["gmm_labels"], dtype=int)
    logger.info(f"Original labels loaded: n={len(orig_labels)}")

    logger.info("Loading original embeddings.npy for PCA sign alignment...")
    orig_embeddings = np.load(CP_DIR / "embeddings.npy")
    logger.info(f"Original embeddings shape: {orig_embeddings.shape}")

    # ------------------------------------------------------------------
    # Step 2: Load trajectories and metadata
    # ------------------------------------------------------------------
    logger.info("Loading trajectory sequences from 01_trajectories_sequences.json...")
    with open(CP_DIR / "01_trajectories_sequences.json") as f:
        trajectories = json.load(f)
    logger.info(f"Loaded {len(trajectories):,} trajectories")

    logger.info("Loading trajectory metadata from 01_trajectories.json...")
    with open(CP_DIR / "01_trajectories.json") as f:
        meta_raw = json.load(f)
    metadata = pd.DataFrame(meta_raw["metadata"])
    if len(trajectories) != len(metadata):
        raise ValueError(
            f"Trajectory/metadata count mismatch: trajectories={len(trajectories)}, metadata={len(metadata)}"
        )
    # ------------------------------------------------------------------
    # Step 3: Compute 90-dim raw features for all trajectories
    # ------------------------------------------------------------------
    from trajectory_tda.data.trajectory_builder import build_windows
    from trajectory_tda.embedding.ngram_embed import _compute_bigrams, _compute_unigrams

    logger.info("Computing raw 90-dim features for all trajectories...")
    traj_raw = np.zeros((len(trajectories), 90), dtype=np.float64)
    for i, traj in enumerate(trajectories):
        traj_raw[i] = np.concatenate([_compute_unigrams(traj), _compute_bigrams(traj)])

    # ------------------------------------------------------------------
    # Step 4: Fit scaler + PCA (svd_solver='full' for exact, deterministic SVD)
    #
    # The original 02_scaler.joblib/02_pca.joblib used PCA(random_state=42) under
    # sklearn 1.3.2 which selected randomized SVD. Under sklearn 1.8.0, the same
    # random_state produces different components due to implementation changes.
    # svd_solver='full' uses LAPACK's exact SVD (dgesdd), which is deterministic and
    # version-independent, giving the globally optimal principal components.
    # ------------------------------------------------------------------
    logger.info("Fitting StandardScaler on trajectory features...")
    scaler = StandardScaler(with_std=True)
    traj_scaled = scaler.fit_transform(traj_raw)

    logger.info("Fitting PCA(n_components=20, svd_solver='full') on scaled trajectory features...")
    pca = PCA(n_components=20, svd_solver="full", random_state=RANDOM_STATE)
    traj_emb = pca.fit_transform(traj_scaled)
    logger.info(f"PCA explained variance: {pca.explained_variance_ratio_.sum():.6f}")

    # Sign-correct PCA components against orig_embeddings.npy for label consistency.
    # PCA eigenvectors are unique only up to sign; correcting ensures that the refit
    # GMM cluster structure maps to the original regime labels consistently.
    sign_flips = []
    for k in range(traj_emb.shape[1]):
        corr = np.corrcoef(traj_emb[:, k], orig_embeddings[:, k])[0, 1]
        if corr < 0:
            pca.components_[k, :] *= -1
            traj_emb[:, k] *= -1
            sign_flips.append(k)
    if sign_flips:
        logger.info(f"Sign-corrected PCA components: {sign_flips}")
    else:
        logger.info("No sign corrections needed")

    max_diff = np.abs(traj_emb - orig_embeddings).max()
    mean_diff = np.abs(traj_emb - orig_embeddings).mean()
    logger.info(f"Refit vs orig embeddings — max abs diff: {max_diff:.6f}, mean: {mean_diff:.6f}")

    # ------------------------------------------------------------------
    # Step 5: Refit GMM on refit embeddings (CRITICAL: same space as windows)
    #
    # GMM is fit on traj_emb (refit), NOT orig_embeddings. This ensures that
    # window embeddings (produced by scaler.transform → pca.transform) are in
    # the same coordinate space as the GMM cluster boundaries.
    # ------------------------------------------------------------------
    refit_path = CP_DIR / f"05_gmm_refit_{TODAY}.pkl"
    logger.info(f"Refitting GMM on refit embeddings (k={N_COMPONENTS})...")
    gmm = GaussianMixture(
        n_components=N_COMPONENTS,
        covariance_type="full",
        n_init=N_INIT,
        random_state=RANDOM_STATE,
    )
    gmm.fit(traj_emb)
    new_traj_labels = gmm.predict(traj_emb)

    label_map = build_label_map(new_traj_labels, orig_labels, N_COMPONENTS)
    disadv_new = {k for k, v in label_map.items() if v in DISADV_ORIG}
    good_new   = {k for k, v in label_map.items() if v in GOOD_ORIG}
    logger.info(f"Label map (new → orig): {label_map}")
    logger.info(f"New labels mapping to R2/R6 (disadvantaged): {disadv_new}")
    logger.info(f"New labels mapping to R1/R4 (good): {good_new}")
    for k in range(N_COMPONENTS):
        n_k = int((new_traj_labels == k).sum())
        logger.info(f"  Refit GMM label {k} → orig R{label_map[k]}: n={n_k}")

    joblib.dump(gmm, refit_path)
    logger.info(f"Refitted GMM saved to {refit_path}")

    # ------------------------------------------------------------------
    # Step 6: Build windows and embed using fitted scaler → PCA pipeline
    # ------------------------------------------------------------------
    logger.info(f"Building {WINDOW_YEARS}-year windows (step={WINDOW_STEP})...")
    windows = build_windows(
        trajectories, metadata, window_years=WINDOW_YEARS, window_step=WINDOW_STEP
    )
    logger.info(f"Total windows: {len(windows):,}")

    logger.info("Computing 90-dim features for all windows...")
    win_raw = np.zeros((len(windows), 90), dtype=np.float64)
    for i, w in enumerate(windows):
        win_raw[i] = np.concatenate([_compute_unigrams(w["states"]), _compute_bigrams(w["states"])])

    logger.info("Applying scaler → PCA → GMM to windows...")
    win_emb     = pca.transform(scaler.transform(win_raw))
    new_win_reg = gmm.predict(win_emb)
    win_reg_mapped = np.array([label_map[k] for k in new_win_reg], dtype=int)

    # ------------------------------------------------------------------
    # Step 7: Load birth years
    # ------------------------------------------------------------------
    all_pidps = metadata["pidp"].dropna().astype(int).unique().tolist()
    birth_years = load_birth_years(all_pidps)

    # ------------------------------------------------------------------
    # Step 8: Build per-person window assignments
    #
    # Escape definition (matching run_priority2.py GOOD_REGIMES={1,4}):
    #   escape = 1 if any subsequent window (after the first) has
    #            orig-mapped regime in GOOD_ORIG={1,4}
    # ------------------------------------------------------------------
    logger.info("Building per-person window assignments...")

    person_windows: dict[int, list[tuple[int, dict]]] = defaultdict(list)
    for idx, w in enumerate(windows):
        person_windows[int(w["pidp"])].append((idx, w))

    assignments = []
    n_starters = 0
    n_escaped  = 0
    n_wa_starters = 0
    n_wa_escaped  = 0

    for pidp, pw_list in person_windows.items():
        pw_sorted = sorted(pw_list, key=lambda x: x[1]["start_year"])
        win_regs  = [int(win_reg_mapped[idx]) for idx, _ in pw_sorted]
        starts    = [w["start_year"] for _, w in pw_sorted]
        ends      = [w["end_year"]   for _, w in pw_sorted]

        first_regime = win_regs[0]
        first_start  = starts[0]

        by = birth_years.get(pidp)
        # Use window midpoint, matching attach_age_to_windows in age_stratified.py
        first_midpoint = (first_start + ends[0]) / 2
        age_fw = int(first_midpoint - by) if by is not None else None

        is_starter = first_regime in DISADV_ORIG
        escape = 0
        if is_starter and len(win_regs) > 1:
            for subsequent in win_regs[1:]:
                if subsequent in GOOD_ORIG:
                    escape = 1
                    break

        if is_starter:
            n_starters += 1
            n_escaped  += escape

        is_wa = age_fw is not None and age_fw < 60
        if is_starter and is_wa:
            n_wa_starters += 1
            n_wa_escaped  += escape

        assignments.append({
            "pidp":                      pidp,
            "n_windows":                 len(pw_sorted),
            "first_window_start_year":   int(first_start),
            "first_window_end_year":     int(ends[0]),
            "first_window_regime":       int(first_regime),
            "escape":                    int(escape),
            "window_regimes":            win_regs,
            "age_first_window":          int(age_fw) if age_fw is not None else None,
            "is_disadvantaged_starter":  bool(is_starter),
        })

    overall_rate = n_escaped  / n_starters    if n_starters    > 0 else 0.0
    wa_rate      = n_wa_escaped / n_wa_starters if n_wa_starters > 0 else 0.0

    logger.info(f"n_starters_all_ages: {n_starters}")
    logger.info(f"n_escaped_all_ages:  {n_escaped}")
    logger.info(f"escape_rate_overall: {overall_rate:.4f}  (ref={REF_RATE:.4f})")
    logger.info(f"n_wa_starters:       {n_wa_starters}  (ref=2163)")
    logger.info(f"n_wa_escaped:        {n_wa_escaped}   (ref=386)")
    logger.info(f"wa_escape_rate:      {wa_rate:.4f}   (ref=0.1785)")

    if n_starters == 0 or abs(n_starters - REF_N_STARTERS) / REF_N_STARTERS > 0.10:
        logger.warning(
            f"WARNING: n_starters={n_starters} deviates >10% from expected {REF_N_STARTERS}. ESCALATE."
        )
    if n_starters > 0 and abs(overall_rate - REF_RATE) / REF_RATE > 0.10:
        logger.warning(
            f"WARNING: escape_rate={overall_rate:.4f} deviates >10% from expected {REF_RATE:.4f}. ESCALATE."
        )

    # ------------------------------------------------------------------
    # Step 9: Save JSON
    # ------------------------------------------------------------------
    def convert(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    output = {
        "run_params": {
            "date":                       TODAY,
            "gmm_n_components":           N_COMPONENTS,
            "gmm_n_init":                 N_INIT,
            "gmm_random_state":           RANDOM_STATE,
            "window_years":               WINDOW_YEARS,
            "window_step":                WINDOW_STEP,
            "disadv_regimes_orig":        sorted(DISADV_ORIG),
            "good_regimes_orig":          sorted(GOOD_ORIG),
            "disadv_new_labels":          sorted(disadv_new),
            "good_new_labels":            sorted(good_new),
            "label_map":                  {str(k): v for k, v in label_map.items()},
            "gmm_refit_path":             str(refit_path),
            "pca_svd_solver":             "full",
            "pca_explained_variance":     float(pca.explained_variance_ratio_.sum()),
            "pca_sign_flips":             sign_flips,
            "embedding_refit_max_diff":   float(max_diff),
        },
        "summary": {
            "n_starters_all_ages":   n_starters,
            "n_escaped_all_ages":    n_escaped,
            "escape_rate_all_ages":  round(overall_rate, 6),
            "n_wa_starters":         n_wa_starters,
            "n_wa_escaped":          n_wa_escaped,
            "wa_escape_rate":        round(wa_rate, 6),
            "ref_n_starters":        REF_N_STARTERS,
            "ref_escape_rate":       REF_RATE,
        },
        "assignments": assignments,
    }

    with open(OUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=convert)

    logger.info(f"Saved: {OUT_PATH}")
    logger.info("=== build_window_assignments.py complete ===")


if __name__ == "__main__":
    main()
