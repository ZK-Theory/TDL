"""
Residualised Persistent Homology (Phase C1).

Removes the dominant severity axis (PC1) from the 7D deprivation point cloud
and computes PH on the residual space. This isolates *patterns* of deprivation
from overall *intensity*, testing whether the topological triviality found in
Phase B was caused by the strong global correlation between domains.

If the residual cloud has non-trivial H₁ topology, it means there are genuine
trade-off structures hidden beneath the dominant correlation.
"""

from __future__ import annotations

import logging
import time

import numpy as np
from sklearn.decomposition import PCA

from poverty_tda.topology.multidim_ph import (
    compute_rips_ph,
    load_deprivation_cloud,
    permutation_test,
    persistence_summary,
)

logger = logging.getLogger(__name__)


def residualise_domains(
    X: np.ndarray,
    n_components_to_remove: int = 1,
) -> tuple[np.ndarray, PCA, dict]:
    """
    Remove the top principal components (the "severity axis") from the
    standardised domain scores.

    Args:
        X: (N, D) z-scored domain scores.
        n_components_to_remove: Number of top PCs to remove (default: 1).

    Returns:
        X_residual: (N, D) residual point cloud after projection.
        pca: Fitted PCA object (for inspection).
        info: Dict with variance explained, loadings, etc.
    """
    n, d = X.shape
    pca = PCA(n_components=d)
    X_pca = pca.fit_transform(X)

    # Zero out the top components
    X_pca_residual = X_pca.copy()
    X_pca_residual[:, :n_components_to_remove] = 0.0

    # Project back to original domain space
    X_residual = pca.inverse_transform(X_pca_residual)

    # Build info dict
    info = {
        "n_components_removed": n_components_to_remove,
        "variance_explained_removed": float(pca.explained_variance_ratio_[:n_components_to_remove].sum()),
        "variance_explained_retained": float(pca.explained_variance_ratio_[n_components_to_remove:].sum()),
        "pc1_loadings": {f"PC{i + 1}": dict(zip(range(d), pca.components_[i].tolist())) for i in range(min(3, d))},
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
    }

    logger.info(
        f"Residualised: removed {n_components_to_remove} PC(s), "
        f"explaining {info['variance_explained_removed']:.1%} of variance. "
        f"Retained {info['variance_explained_retained']:.1%}."
    )

    return X_residual, pca, info


def compute_residualised_ph(
    region: str = "west_midlands",
    n_components_to_remove: int = 1,
    max_dim: int = 1,
    do_permutation: int = 0,
) -> tuple[dict, object, object]:
    """
    Full C1 pipeline: load data, residualise, compute PH, compare with raw.

    Returns:
        A 3-tuple of:
            results: Dict with raw and residual PH results, PCA info, and optional
                permutation test results.
            ph_raw: Persistent homology object computed on the raw point cloud.
            ph_resid: Persistent homology object computed on the residualised point cloud.
    """
    t0 = time.time()

    # Load the raw point cloud
    X_raw, lsoa_codes, domain_names = load_deprivation_cloud(region=region)
    n, d = X_raw.shape
    logger.info(f"Loaded {region}: {n} LSOAs × {d} domains")

    # --- Raw PH (for comparison) ---
    logger.info("Computing RAW PH...")
    ph_raw = compute_rips_ph(X_raw, max_dim=max_dim)
    ph_raw.domain_names = domain_names
    summary_raw = persistence_summary(ph_raw)

    # --- Residualised PH ---
    logger.info("Residualising...")
    X_residual, pca, pca_info = residualise_domains(X_raw, n_components_to_remove=n_components_to_remove)

    # Log the PC1 loadings in terms of domain names
    pc1 = pca.components_[0]
    pc1_by_domain = sorted(zip(domain_names, pc1), key=lambda x: abs(x[1]), reverse=True)
    logger.info("PC1 loadings (the 'severity axis'):")
    for name, loading in pc1_by_domain:
        logger.info(f"  {name}: {loading:+.3f}")

    logger.info("Computing RESIDUALISED PH...")
    ph_resid = compute_rips_ph(X_residual, max_dim=max_dim)
    ph_resid.domain_names = domain_names
    summary_resid = persistence_summary(ph_resid)

    # --- Log comparison ---
    logger.info("\n" + "=" * 70)
    logger.info("COMPARISON: RAW vs RESIDUALISED")
    logger.info("=" * 70)
    for dim_key in ["H0", "H1"]:
        raw_s = summary_raw.get(dim_key, {})
        res_s = summary_resid.get(dim_key, {})
        logger.info(
            f"  {dim_key} RAW:   {raw_s.get('n_finite', 0)} features, "
            f"max_pers={raw_s.get('max_persistence', 0):.4f}, "
            f"total_pers={raw_s.get('total_persistence', 0):.3f}"
        )
        logger.info(
            f"  {dim_key} RESID: {res_s.get('n_finite', 0)} features, "
            f"max_pers={res_s.get('max_persistence', 0):.4f}, "
            f"total_pers={res_s.get('total_persistence', 0):.3f}"
        )

    # --- Permutation test on residualised cloud ---
    perm_raw = None
    perm_resid = None
    if do_permutation > 0:
        logger.info(f"\nRunning permutation tests ({do_permutation} permutations)...")
        logger.info("  Permutation test on RAW cloud...")
        perm_raw = permutation_test(
            X_raw,
            n_permutations=do_permutation,
            max_dim=max_dim,
            statistic="max_persistence",
        )
        logger.info("  Permutation test on RESIDUALISED cloud...")
        perm_resid = permutation_test(
            X_residual,
            n_permutations=do_permutation,
            max_dim=max_dim,
            statistic="max_persistence",
        )

    elapsed = time.time() - t0

    results = {
        "region": region,
        "n_lsoas": int(n),
        "n_dimensions": int(d),
        "domain_names": domain_names,
        "elapsed_seconds": elapsed,
        "pca_info": {
            "n_components_removed": n_components_to_remove,
            "variance_explained_removed": pca_info["variance_explained_removed"],
            "variance_explained_retained": pca_info["variance_explained_retained"],
            "explained_variance_ratio": pca_info["explained_variance_ratio"],
            "pc1_loadings": dict(zip(domain_names, pca.components_[0].tolist())),
        },
        "raw": {
            "persistence_summary": {
                k: {kk: vv for kk, vv in v.items() if kk != "features"} for k, v in summary_raw.items()
            },
            "permutation_test": perm_raw,
        },
        "residualised": {
            "persistence_summary": {
                k: {kk: vv for kk, vv in v.items() if kk != "features"} for k, v in summary_resid.items()
            },
            "permutation_test": perm_resid,
        },
    }

    return results, ph_raw, ph_resid
