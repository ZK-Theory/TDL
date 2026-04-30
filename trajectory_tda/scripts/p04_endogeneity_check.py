# Research context: TDA-Research/03-Papers/P04/_project.md
# Purpose: Income-proxy endogeneity check for P04 AoAS submission.
#   Regresses the income proxy (mean income band per trajectory) on PC1-PC20
#   of the P01 PCA embedding. Reports R², adjusted R², and per-PC correlations
#   to assess whether the income parameter in the bifiltration is redundant with
#   the Rips geometry. Computation is fully deterministic (OLS, no stochastic steps).

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from scipy.stats import pearsonr

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
CHECKPOINT_DIR = ROOT / "results" / "trajectory_tda_integration"
OUTPUT_FILE = ROOT / "results" / "p04_exploration" / "endogeneity_check.json"


def load_data() -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Load PCA embedding and income proxy.

    Returns:
        embeddings: (N, 20) array — PC1-PC20 scores.
        income_scores: (N,) array — mean income band per trajectory.
    """
    from trajectory_tda.topology.multipers_bifiltration import load_embeddings_and_income

    return load_embeddings_and_income(checkpoint_dir=CHECKPOINT_DIR)


def run_endogeneity_check(
    embeddings: NDArray[np.float64],
    income_scores: NDArray[np.float64],
) -> dict:
    """OLS regression of income proxy on PC1-PC20.

    Args:
        embeddings: (N, 20) PCA scores.
        income_scores: (N,) income proxy values.

    Returns:
        Results dict with R², adjusted R², per-PC correlations.
    """
    n, p = embeddings.shape
    logger.info("Running OLS: income ~ PC1-PC20 (n=%d, p=%d)", n, p)

    reg = LinearRegression(fit_intercept=True)
    reg.fit(embeddings, income_scores)
    predicted = reg.predict(embeddings)

    r2 = float(r2_score(income_scores, predicted))
    adj_r2 = float(1 - (1 - r2) * (n - 1) / (n - p - 1))

    # Per-PC Pearson correlations
    pc_correlations = []
    for i in range(p):
        r, pval = pearsonr(embeddings[:, i], income_scores)
        pc_correlations.append({
            "pc": i + 1,
            "r": float(r),
            "abs_r": float(abs(r)),
            "p_value": float(pval),
            "coef": float(reg.coef_[i]),
        })

    pc_correlations.sort(key=lambda x: x["abs_r"], reverse=True)

    # Interpretation tier
    if r2 < 0.15:
        tier = "low"
        interpretation = (
            "Concern moot: income proxy is largely orthogonal to PCA geometry. "
            "Report R² in §4.1 as one sentence."
        )
    elif r2 < 0.40:
        tier = "moderate"
        interpretation = (
            "Income correlates with some PCA axes but bifiltration still adds "
            "joint topology information. Acknowledge in §3; argue the bifiltration "
            "decomposes joint structure beyond any single-axis projection."
        )
    else:
        tier = "high"
        interpretation = (
            "Income substantially encoded in PCA geometry. Add a paragraph in §3 "
            "explaining that bifiltration decomposes joint topology (distance × income "
            "simultaneously), not just a 1D projection. Cite permutation null (p<0.001) "
            "as evidence of added information beyond the geometric projection."
        )

    return {
        "n": n,
        "n_pcs": p,
        "r2": r2,
        "adjusted_r2": adj_r2,
        "interpretation_tier": tier,
        "interpretation": interpretation,
        "top3_pcs": pc_correlations[:3],
        "all_pc_correlations": pc_correlations,
        "intercept": float(reg.intercept_),
    }


def main() -> None:
    logger.info("Loading embedding and income proxy...")
    embeddings, income_scores = load_data()
    logger.info(
        "Embedding shape: %s | Income: mean=%.3f std=%.3f",
        embeddings.shape,
        income_scores.mean(),
        income_scores.std(),
    )

    results = run_endogeneity_check(embeddings, income_scores)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w") as f:
        json.dump(results, f, indent=2)
    logger.info("Results saved to %s", OUTPUT_FILE)

    # Summary
    print("\n" + "=" * 60)
    print("P04 Income-Proxy Endogeneity Check")
    print("=" * 60)
    print(f"  N:             {results['n']:,}")
    print(f"  R²:            {results['r2']:.4f}")
    print(f"  Adjusted R²:   {results['adjusted_r2']:.4f}")
    print(f"  Tier:          {results['interpretation_tier'].upper()}")
    print(f"\nTop 3 PCs by |r|:")
    for pc in results["top3_pcs"]:
        print(f"  PC{pc['pc']:02d}  r={pc['r']:+.4f}  coef={pc['coef']:+.4f}")
    print(f"\nInterpretation:\n  {results['interpretation']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
