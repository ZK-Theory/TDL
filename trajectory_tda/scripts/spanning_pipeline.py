"""
Build spanning trajectories (persons appearing in both BHPS and USoc).
Saves spanning trajectories and metadata for TDA pipeline.

Run: python trajectory_tda/scripts/spanning_pipeline.py
"""

import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import json
import logging
import time
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
CHECKPOINT_DIR = Path("results/trajectory_tda_spanning")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

t0 = time.time()

# ─── Step 1: Load all employment data (BHPS + USoc) ───
logger.info("Step 1/5: Loading employment status (BHPS + USoc)...")
from trajectory_tda.data.employment_status import extract_employment_status

emp_df = extract_employment_status("trajectory_tda/data")
logger.info(f"  Employment: {len(emp_df)} obs, {emp_df['pidp'].nunique()} persons")

# ─── Step 2: Load all income data (BHPS + USoc) ───
logger.info("Step 2/5: Loading income bands (BHPS + USoc)...")
from trajectory_tda.data.income_band import extract_income_bands

inc_df = extract_income_bands("trajectory_tda/data")
logger.info(f"  Income: {len(inc_df)} obs, {inc_df['pidp'].nunique()} persons")

# ─── Step 3: Build all trajectories ───
logger.info("Step 3/5: Building all trajectories...")
from trajectory_tda.data.trajectory_builder import build_trajectories

trajectories, metadata = build_trajectories(emp_df=emp_df, inc_df=inc_df)
logger.info(f"  Total: {len(trajectories)} trajectories")

era_counts = metadata["survey_era"].value_counts()
for era, count in era_counts.items():
    sub = metadata[metadata["survey_era"] == era]
    logger.info(
        f"    {era}: n={count}, mean_len={sub['n_years'].mean():.1f}, "
        f"range={sub['start_year'].min()}-{sub['end_year'].max()}"
    )

# ─── Step 4: Filter spanning trajectories ───
spanning_mask = metadata["survey_era"] == "spanning"
n_spanning = spanning_mask.sum()
logger.info(f"\nSpanning trajectories: {n_spanning}")

if n_spanning < 500:
    logger.warning(
        f"Only {n_spanning} spanning trajectories (< 500 minimum). "
        f"Saving metadata but skipping TDA pipeline."
    )
    # Still save the data for documentation
    result = {
        "n_total": len(trajectories),
        "n_spanning": int(n_spanning),
        "n_bhps_only": int(era_counts.get("bhps_only", 0)),
        "n_usoc_only": int(era_counts.get("usoc_only", 0)),
        "sufficient_for_tda": False,
        "elapsed": time.time() - t0,
    }
    with open(CHECKPOINT_DIR / "results_full.json", "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Results saved. Elapsed: {time.time() - t0:.1f}s")
    sys.exit(0)

# Extract spanning subset
spanning_indices = metadata.index[spanning_mask].tolist()
spanning_trajs = [trajectories[i] for i in spanning_indices]
spanning_meta = metadata.loc[spanning_mask].reset_index(drop=True)

logger.info(
    f"  Spanning: n={len(spanning_trajs)}, "
    f"mean_len={spanning_meta['n_years'].mean():.1f}, "
    f"range={spanning_meta['start_year'].min()}-{spanning_meta['end_year'].max()}"
)

# Save spanning trajectory data
np.save(
    SCRIPT_DIR / "spanning_trajectories.npy",
    np.array(spanning_trajs, dtype=object),
    allow_pickle=True,
)
spanning_meta.to_pickle(SCRIPT_DIR / "spanning_metadata.pkl")

# Save trajectory checkpoint
with open(CHECKPOINT_DIR / "01_trajectories.json", "w") as f:
    json.dump(
        {"metadata": spanning_meta.to_dict(), "n": len(spanning_trajs)},
        f,
        indent=2,
        default=str,
    )
with open(CHECKPOINT_DIR / "01_trajectories_sequences.json", "w") as f:
    json.dump(spanning_trajs, f)

# ─── Step 5: Run TDA pipeline on spanning trajectories ───
logger.info("Step 5/5: Running TDA pipeline on spanning trajectories...")

from trajectory_tda.analysis.cycle_detection import detect_cycles
from trajectory_tda.analysis.regime_discovery import discover_regimes
from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories
from trajectory_tda.topology.trajectory_ph import compute_trajectory_ph

# Embed
logger.info("  Embedding...")
embeddings, embed_info = ngram_embed(
    spanning_trajs, include_bigrams=True, tfidf=False, pca_dim=20
)
logger.info(f"    Shape: {embeddings.shape}")
np.save(CHECKPOINT_DIR / "embeddings.npy", embeddings)

# PH
n_landmarks = min(5000, len(spanning_trajs))
logger.info(f"  Computing PH (landmarks={n_landmarks})...")
ph_result = compute_trajectory_ph(
    embeddings, max_dim=1, n_landmarks=n_landmarks, method="maxmin_vr", validate=True
)
logger.info(f"    PH in {ph_result['elapsed_seconds']:.1f}s")

# Permutation tests (reduced to 50 perms for speed)
logger.info("  Permutation tests (50 perms)...")
embed_kwargs = {"include_bigrams": True, "tfidf": False, "pca_dim": 20}
null_results = {}
for null_type in ["label_shuffle", "order_shuffle", "markov"]:
    try:
        nr = permutation_test_trajectories(
            embeddings=embeddings,
            trajectories=spanning_trajs,
            null_type=null_type,
            n_permutations=50,
            max_dim=1,
            n_landmarks=n_landmarks,
            statistic="total_persistence",
            embed_kwargs=embed_kwargs,
        )
        null_results[null_type] = nr
        logger.info(f"    {null_type}: done")
    except Exception as e:
        logger.warning(f"    {null_type} failed: {e}")
        null_results[null_type] = {"error": str(e)}

# Analysis
logger.info("  Regime discovery + cycle detection...")
regimes = discover_regimes(embeddings, spanning_trajs, ph_result=ph_result)
cycles = detect_cycles(ph_result, embeddings, spanning_trajs)


# ─── Save everything ───
def convert(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): convert(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert(v) for v in obj]
    return obj


result = {
    "n_total": len(trajectories),
    "n_spanning": int(n_spanning),
    "n_bhps_only": int(era_counts.get("bhps_only", 0)),
    "n_usoc_only": int(era_counts.get("usoc_only", 0)),
    "sufficient_for_tda": True,
    "embedding_shape": list(embeddings.shape),
    "k_optimal": regimes["k_optimal"],
    "n_persistent_loops": cycles["n_persistent_loops"],
    "null_p_values": {},
    "elapsed": time.time() - t0,
}

for nt, nr in null_results.items():
    if "error" not in nr:
        for dim_key in ["H0", "H1"]:
            if dim_key in nr:
                result["null_p_values"][f"{nt}_{dim_key}"] = nr[dim_key].get("p_value")

with open(CHECKPOINT_DIR / "04_nulls.json", "w") as f:
    json.dump(convert(null_results), f, indent=2)

with open(CHECKPOINT_DIR / "05_analysis.json", "w") as f:
    json.dump(
        convert(
            {
                "regimes": {
                    "k_optimal": regimes["k_optimal"],
                    "profiles": regimes.get("regime_profiles", {}),
                },
                "cycles": {
                    "n_persistent_loops": cycles["n_persistent_loops"],
                    "h1_summary": cycles.get("h1_summary", {}),
                },
                "gmm_labels": regimes["gmm_labels"],
            }
        ),
        f,
        indent=2,
    )

with open(CHECKPOINT_DIR / "results_full.json", "w") as f:
    json.dump(convert(result), f, indent=2)

elapsed = time.time() - t0
logger.info("=" * 60)
logger.info(f"Spanning Pipeline complete in {elapsed:.1f}s")
logger.info(f"  Total trajectories: {len(trajectories)}")
logger.info(f"  Spanning: {n_spanning}")
logger.info(f"  Regimes (k): {regimes['k_optimal']}")
logger.info(f"  H1 loops: {cycles['n_persistent_loops']}")
logger.info(f"  Results: {CHECKPOINT_DIR}")
logger.info("=" * 60)
