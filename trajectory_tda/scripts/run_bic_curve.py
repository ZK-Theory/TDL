# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Full BIC curve over k=3..15 for GMM component-count selection
"""
Fits GaussianMixture(covariance_type='full', n_init=5, random_state=42) for each
k in {3,...,15} on the PCA-20D career-trajectory embedding, computes BIC, and
reports ΔBIC on the Kass-Raftery scale.

Note: original GMM (regime_discovery.py) used n_init=3 with default covariance_type='full'.
This BIC curve uses n_init=5 for more thorough optimisation; the final k=7 fit
for regime labels is not re-used here.

Run: uv run --env-file .env python trajectory_tda/scripts/run_bic_curve.py
"""

import json
import logging
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.mixture import GaussianMixture

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
EMBEDDING_PATH = ROOT / "results" / "trajectory_tda_integration" / "embeddings.npy"
OUT_DIR = ROOT / "results" / "trajectory_tda_integration" / "stage1"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / f"bic_curve_{date.today()}.json"

GMM_PARAMS = {"covariance_type": "full", "n_init": 5, "random_state": 42, "max_iter": 200}
K_RANGE = range(3, 16)


def kass_raftery(delta: float) -> str:
    """Return Kass-Raftery scale label for |ΔBIC|."""
    if abs(delta) < 2:
        return "weak"
    if abs(delta) < 6:
        return "positive"
    if abs(delta) < 10:
        return "strong"
    return "very strong"


def main() -> None:
    if not EMBEDDING_PATH.exists():
        log.error("Embedding file not found: %s", EMBEDDING_PATH)
        raise FileNotFoundError(f"Required embedding file missing: {EMBEDDING_PATH}")
    log.info("Loading PCA-20D embedding from %s", EMBEDDING_PATH)
    embedding: np.ndarray = np.load(EMBEDDING_PATH)
    log.info("Embedding shape: %s", embedding.shape)
    if embedding.ndim != 2 or embedding.shape[1] != 20:
        log.error("Expected 2D array with 20 features, got shape %s", embedding.shape)
        raise ValueError(f"Invalid embedding shape: {embedding.shape}")
    if len(embedding) == 0:
        log.error("Embedding array is empty")
        raise ValueError("Cannot fit GMM on empty embedding")

    bic_by_k: dict[int, float] = {}
    for k in K_RANGE:
        log.info("Fitting GMM k=%d …", k)
        gmm = GaussianMixture(n_components=k, **GMM_PARAMS)
        gmm.fit(embedding)
        bic_by_k[k] = float(gmm.bic(embedding))
        log.info("  k=%d  BIC=%.2f", k, bic_by_k[k])

    best_k = min(bic_by_k, key=bic_by_k.__getitem__)
    bic_k7 = bic_by_k[7]
    delta_vs_best = bic_k7 - bic_by_k[best_k]
    delta_k6 = bic_k7 - bic_by_k[6]
    delta_k8 = bic_k7 - bic_by_k[8]

    # Negative delta_vs_best means k=7 IS the minimum (best_k==7)
    if best_k == 7:
        kr_conclusion = (
            f"k=7 minimises BIC (best_k=7). "
            f"ΔBIC(k=7, k=6)={delta_k6:.1f} [{kass_raftery(delta_k6)}], "
            f"ΔBIC(k=7, k=8)={delta_k8:.1f} [{kass_raftery(delta_k8)}]. "
            f"k=7 is well-supported."
        )
    else:
        kr_conclusion = (
            f"best_k={best_k} (BIC={bic_by_k[best_k]:.1f}). "
            f"ΔBIC(k=7, k={best_k})={delta_vs_best:.1f} "
            f"[{kass_raftery(delta_vs_best)} evidence against k=7]. "
            f"ΔBIC(k=7, k=6)={delta_k6:.1f} [{kass_raftery(delta_k6)}], "
            f"ΔBIC(k=7, k=8)={delta_k8:.1f} [{kass_raftery(delta_k8)}]."
        )

    log.info("best_k=%d  ΔBIC(k=7,best)=%.2f  kr=%s", best_k, delta_vs_best, kass_raftery(delta_vs_best))

    result = {
        "bic_by_k": {str(k): v for k, v in bic_by_k.items()},
        "best_k": best_k,
        "delta_bic_vs_best": delta_vs_best,
        "delta_bic_k6": delta_k6,
        "delta_bic_k8": delta_k8,
        "kass_raftery_interpretation": kr_conclusion,
        "gmm_params": GMM_PARAMS,
        "embedding_source": str(EMBEDDING_PATH),
        "note_original_pipeline": "Original regime_discovery.py used n_init=3; this BIC curve uses n_init=5 per task spec.",
    }

    with OUT_PATH.open("w") as f:
        json.dump(result, f, indent=2)
    log.info("Saved BIC results to %s", OUT_PATH)


if __name__ == "__main__":
    main()
