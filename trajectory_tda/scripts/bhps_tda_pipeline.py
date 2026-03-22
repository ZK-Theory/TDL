"""
BHPS-era TDA pipeline (Steps 3-6).
Uses pre-built BHPS trajectories from bhps_pipeline.py output.

Run: python trajectory_tda/scripts/bhps_tda_pipeline.py
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
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
CHECKPOINT_DIR = Path("results/trajectory_tda_bhps")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

t0 = time.time()

# ─── Load pre-built BHPS trajectories ───
logger.info("Loading BHPS trajectories...")
trajectories_raw = np.load(SCRIPT_DIR / "bhps_trajectories.npy", allow_pickle=True)
trajectories = [list(t) for t in trajectories_raw]
metadata = pd.read_pickle(SCRIPT_DIR / "bhps_metadata.pkl")
logger.info(f"Loaded {len(trajectories)} BHPS-era trajectories")

# Save trajectory checkpoint
cp_data = {"metadata": metadata.to_dict(), "n": len(trajectories)}
with open(CHECKPOINT_DIR / "01_trajectories.json", "w") as f:
    json.dump(cp_data, f, indent=2, default=str)
with open(CHECKPOINT_DIR / "01_trajectories_sequences.json", "w") as f:
    json.dump(trajectories, f)

# ─── Step 3: Embed (n-grams + PCA-20D) ───
logger.info("=" * 60)
logger.info("Step 3: Embedding BHPS trajectories (n-grams + PCA-20D)")
logger.info("=" * 60)

from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.utils.model_io import save_model

embeddings, embed_info = ngram_embed(
    trajectories,
    include_bigrams=True,
    tfidf=False,
    pca_dim=20,
)
logger.info(f"Embeddings shape: {embeddings.shape}")

# Save embedding checkpoint
embed_cp = {
    "shape": list(embeddings.shape),
    "info": {k: v for k, v in embed_info.items() if k != "fitted_models"},
}
with open(CHECKPOINT_DIR / "02_embedding.json", "w") as f:
    json.dump(embed_cp, f, indent=2, default=str)
np.save(CHECKPOINT_DIR / "embeddings.npy", embeddings)

fitted_models = embed_info.get("fitted_models", {})
if fitted_models.get("scaler") is not None:
    save_model(fitted_models["scaler"], CHECKPOINT_DIR / "02_scaler.joblib")
if fitted_models.get("reducer") is not None:
    save_model(fitted_models["reducer"], CHECKPOINT_DIR / "02_pca.joblib")

# ─── Step 4: Compute PH (maxmin VR, L=5000) ───
logger.info("=" * 60)
logger.info("Step 4: Computing persistent homology (maxmin VR, L=5000)")
logger.info("=" * 60)

from trajectory_tda.topology.trajectory_ph import compute_trajectory_ph

ph_result = compute_trajectory_ph(
    embeddings,
    max_dim=1,
    n_landmarks=5000,
    method="maxmin_vr",
    validate=True,
)
logger.info(f"PH computed in {ph_result['elapsed_seconds']:.1f}s")

ph_cp = {
    "n_landmarks": ph_result["n_landmarks"],
    "elapsed": ph_result["elapsed_seconds"],
    "summaries": {
        k: {
            dk: {kk: vv for kk, vv in dv.items() if kk != "features"}
            for dk, dv in v.items()
        }
        for k, v in ph_result.get("summaries", {}).items()
    },
}
with open(CHECKPOINT_DIR / "03_ph.json", "w") as f:
    json.dump(ph_cp, f, indent=2, default=str)

# Save raw persistence diagrams
raw_diagrams = {}
for method_key in ["witness", "maxmin_vr"]:
    if method_key in ph_result:
        ph_obj = ph_result[method_key]
        raw_diagrams[method_key] = {
            str(dim): dgm.tolist() for dim, dgm in ph_obj.dgms.items()
        }
        if hasattr(ph_obj, "landmark_indices") and ph_obj.landmark_indices is not None:
            np.save(
                CHECKPOINT_DIR / f"03_landmark_indices_{method_key}.npy",
                ph_obj.landmark_indices,
            )
with open(CHECKPOINT_DIR / "03_ph_diagrams.json", "w") as f:
    json.dump(raw_diagrams, f, indent=2)

# ─── Step 5: Permutation tests ───
logger.info("=" * 60)
logger.info("Step 5: Permutation tests (all 4 null models, 100 perms)")
logger.info("=" * 60)

from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories

null_types = ["label_shuffle", "cohort_shuffle", "order_shuffle", "markov"]
embed_kwargs = {"include_bigrams": True, "tfidf": False, "pca_dim": 20}
null_results = {}

for null_type in null_types:
    logger.info(f"  Running {null_type} null...")
    try:
        nr = permutation_test_trajectories(
            embeddings=embeddings,
            trajectories=trajectories,
            null_type=null_type,
            n_permutations=100,
            max_dim=1,
            n_landmarks=5000,
            statistic="total_persistence",
            markov_order=1,
            embed_kwargs=embed_kwargs,
        )
        null_results[null_type] = nr
        logger.info(f"    {null_type}: p={nr.get('p_value', 'N/A')}")
    except Exception as e:
        logger.warning(f"    {null_type} failed: {e}")
        null_results[null_type] = {"error": str(e)}

with open(CHECKPOINT_DIR / "04_nulls.json", "w") as f:

    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        return obj

    json.dump(convert(null_results), f, indent=2)

# ─── Step 6: Analysis (GMM regimes, cycle detection) ───
logger.info("=" * 60)
logger.info("Step 6: Analysis (regimes, cycles)")
logger.info("=" * 60)

from trajectory_tda.analysis.cycle_detection import detect_cycles
from trajectory_tda.analysis.regime_discovery import discover_regimes

regimes = discover_regimes(embeddings, trajectories, ph_result=ph_result)
logger.info(f"Optimal k={regimes['k_optimal']}")

# Regime exemplars
regime_exemplars = {}
gmm_labels = regimes["gmm_labels"]
for label in np.unique(gmm_labels):
    mask = gmm_labels == label
    cluster_embeddings = embeddings[mask]
    cluster_indices = np.where(mask)[0]
    centroid = cluster_embeddings.mean(axis=0)
    dists = np.linalg.norm(cluster_embeddings - centroid, axis=1)
    top5 = np.argsort(dists)[:5]
    exemplar_indices = cluster_indices[top5].tolist()
    regime_exemplars[str(label)] = {
        "indices": exemplar_indices,
        "trajectories": [trajectories[i] for i in exemplar_indices],
    }

# Cycle detection
cycles = detect_cycles(ph_result, embeddings, trajectories)

# Save analysis
analysis_result = {
    "regimes": {
        "k_optimal": regimes["k_optimal"],
        "profiles": {
            str(k): {kk: vv for kk, vv in v.items() if kk != "composition"}
            for k, v in regimes["regime_profiles"].items()
        },
    },
    "cycles": {
        "n_persistent_loops": cycles["n_persistent_loops"],
        "h1_summary": cycles.get("h1_summary", {}),
    },
    "regime_exemplars": regime_exemplars,
    "gmm_labels": gmm_labels.tolist(),
}
with open(CHECKPOINT_DIR / "05_analysis.json", "w") as f:
    json.dump(convert(analysis_result), f, indent=2)

if regimes.get("gmm_object") is not None:
    save_model(regimes["gmm_object"], CHECKPOINT_DIR / "05_gmm.joblib")

# ─── Summary ───
elapsed = time.time() - t0
summary = {
    "n_trajectories": len(trajectories),
    "embedding_shape": list(embeddings.shape),
    "k_optimal": regimes["k_optimal"],
    "n_persistent_loops": cycles["n_persistent_loops"],
    "null_p_values": {k: v.get("p_value", "error") for k, v in null_results.items()},
    "elapsed_total": elapsed,
}

with open(CHECKPOINT_DIR / "results_full.json", "w") as f:
    json.dump(convert(summary), f, indent=2)

logger.info("=" * 60)
logger.info(f"BHPS Pipeline complete in {elapsed:.1f}s")
logger.info(f"  Trajectories: {len(trajectories)}")
logger.info(f"  Regimes (k): {regimes['k_optimal']}")
logger.info(f"  H1 loops: {cycles['n_persistent_loops']}")
logger.info(f"  Null p-values: {summary['null_p_values']}")
logger.info(f"  Results saved to: {CHECKPOINT_DIR}")
logger.info("=" * 60)
