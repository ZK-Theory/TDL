"""
Phase B2: Regional Exploration of Multidimensional Deprivation Topology.

Runs Rips persistent homology on the 7D IMD domain score point cloud for
specified regions and produces persistence diagrams, Betti curves, and
topological summaries.

Usage:
    python -m poverty_tda.validation.run_multidim_ph --region west_midlands
    python -m poverty_tda.validation.run_multidim_ph --region greater_manchester
    python -m poverty_tda.validation.run_multidim_ph --all
    python -m poverty_tda.validation.run_multidim_ph --region west_midlands --permutation-test 20
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.topology.multidim_ph import (
    PHResult,
    betti_curve,
    compute_rips_ph,
    load_deprivation_cloud,
    permutation_test,
    persistence_summary,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "multidim_ph_results"


def plot_persistence_diagram(ph: PHResult, title: str, save_path: Path):
    """Plot persistence diagram for H0, H1, H2."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    colors = {0: "#2196F3", 1: "#FF5722", 2: "#4CAF50"}
    labels = {0: "H₀ (Components)", 1: "H₁ (Loops)", 2: "H₂ (Voids)"}

    max_val = 0
    for dim in range(3):
        ax = axes[dim]
        if dim in ph.dgms:
            dgm = ph.dgms[dim]
            finite = dgm[dgm[:, 1] != np.inf]
            if len(finite) > 0:
                births = finite[:, 0]
                deaths = finite[:, 1]
                lifetimes = deaths - births
                max_lt = lifetimes.max() if len(lifetimes) > 0 else 1
                sizes = np.maximum(10, 100 * lifetimes / max_lt)
                ax.scatter(births, deaths, c=colors[dim], s=sizes, alpha=0.6, edgecolors="white", linewidths=0.5)
                max_val = max(max_val, deaths.max())

        # Diagonal
        lim = max_val * 1.05 if max_val > 0 else 1
        ax.plot([0, lim], [0, lim], "k--", alpha=0.3, linewidth=0.5)
        ax.set_xlim(-0.05, lim)
        ax.set_ylim(-0.05, lim)
        ax.set_xlabel("Birth", fontsize=11)
        ax.set_ylabel("Death", fontsize=11)
        n_feat = len(ph.dgms[dim][ph.dgms[dim][:, 1] != np.inf]) if dim in ph.dgms else 0
        ax.set_title(f"{labels[dim]} ({n_feat} features)", fontsize=12)
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.2)

    fig.suptitle(title, fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved persistence diagram: {save_path}")


def plot_betti_curves(ph: PHResult, title: str, save_path: Path):
    """Plot Betti curves β₀(ε), β₁(ε), β₂(ε)."""
    curves = betti_curve(ph, n_points=300)

    fig, ax = plt.subplots(figsize=(12, 5))
    colors = {0: "#2196F3", 1: "#FF5722", 2: "#4CAF50"}
    labels = {0: "β₀ (Components)", 1: "β₁ (Loops)", 2: "β₂ (Voids)"}

    for dim in range(3):
        if dim in curves:
            eps, betti = curves[dim]
            if betti.max() > 0:
                ax.plot(eps, betti, color=colors[dim], label=labels[dim], linewidth=2)

    ax.set_xlabel("Filtration parameter ε", fontsize=12)
    ax.set_ylabel("Betti number", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.2)
    ax.set_xlim(0, None)
    ax.set_ylim(0, None)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved Betti curves: {save_path}")


def plot_barcode(ph: PHResult, title: str, save_path: Path, max_bars: int = 50):
    """Plot persistence barcode (top features by lifetime)."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    colors = {0: "#2196F3", 1: "#FF5722", 2: "#4CAF50"}
    labels = {0: "H₀ (Components)", 1: "H₁ (Loops)", 2: "H₂ (Voids)"}

    for dim in range(3):
        ax = axes[dim]
        if dim not in ph.dgms:
            ax.set_title(f"{labels[dim]} (0 features)", fontsize=12)
            continue

        dgm = ph.dgms[dim]
        # Get all features with finite death, sorted by lifetime
        finite = dgm[dgm[:, 1] != np.inf]
        if len(finite) == 0:
            ax.set_title(f"{labels[dim]} (0 features)", fontsize=12)
            continue

        lifetimes = finite[:, 1] - finite[:, 0]
        order = np.argsort(lifetimes)[::-1][:max_bars]
        features = finite[order]

        for i, (birth, death) in enumerate(features):
            ax.barh(
                i, death - birth, left=birth, height=0.8, color=colors[dim], alpha=0.7, edgecolor="white", linewidth=0.3
            )

        ax.set_xlabel("Filtration ε", fontsize=11)
        ax.set_ylabel("Feature index", fontsize=11)
        ax.set_title(f"{labels[dim]} (top {len(features)})", fontsize=12)
        ax.invert_yaxis()
        ax.grid(True, alpha=0.2, axis="x")

    fig.suptitle(title, fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved barcode: {save_path}")


def analyze_h1_domain_variation(ph: PHResult, X: np.ndarray, domain_names: list[str], n_top: int = 10) -> list[dict]:
    """
    For each persistent H1 cycle, identify which deprivation domains
    vary most among the vertices that participate in the cycle.

    Uses cocycle information from ripser to identify representative vertices.
    """
    h1_features = ph.h_features(dim=1, min_persistence=0.0)
    if not h1_features:
        logger.info("No H1 features found.")
        return []

    # Sort by persistence (descending)
    h1_features.sort(key=lambda x: x[1] - x[0], reverse=True)
    h1_features = h1_features[:n_top]

    results = []
    for i, (birth, death) in enumerate(h1_features):
        lifetime = death - birth

        # For each H1 feature, find points that are "close" to the
        # birth/death scale — these participate in the cycle
        from scipy.spatial.distance import pdist, squareform

        D = squareform(pdist(X))

        # Points connected at the death scale form the cycle
        connected = D <= death
        # Find points with many connections at this scale (cycle participants)
        connectivity = connected.sum(axis=1)

        # Take points in the most connected quartile at this scale
        threshold = np.percentile(connectivity, 75)
        cycle_mask = connectivity >= threshold
        cycle_points = X[cycle_mask]

        if len(cycle_points) < 3:
            continue

        domain_variances = np.var(cycle_points, axis=0)
        ranking = np.argsort(domain_variances)[::-1]

        result = {
            "rank": i + 1,
            "birth": float(birth),
            "death": float(death),
            "lifetime": float(lifetime),
            "n_cycle_points": int(cycle_mask.sum()),
            "domain_variances": {
                domain_names[j]: round(float(domain_variances[j]), 4) for j in range(len(domain_names))
            },
            "top_varying_domains": [domain_names[j] for j in ranking[:3]],
        }
        results.append(result)
        logger.info(f"  H1 #{i + 1}: lifetime={lifetime:.3f}, top varying: {result['top_varying_domains']}")

    return results


def run_region(region: str, do_permutation: int = 0) -> dict:
    """Run full PH analysis for a region."""
    logger.info("=" * 70)
    logger.info(f"MULTIDIMENSIONAL PH: {region.upper()}")
    logger.info("=" * 70)
    t0 = time.time()

    # Load data
    X, lsoa_codes, domain_names = load_deprivation_cloud(region=region)

    # Compute PH
    # Use max_dim=1 (H0+H1) to avoid exponential combinatorial explosion of 3-simplices (H2)
    ph = compute_rips_ph(X, max_dim=1)
    ph.lsoa_codes = lsoa_codes
    ph.domain_names = domain_names
    ph.point_cloud = X

    # Summary
    summary = persistence_summary(ph)
    logger.info("\n" + "=" * 70)
    logger.info("PERSISTENCE SUMMARY")
    logger.info("=" * 70)
    for dim_key in ["H0", "H1", "H2"]:
        if dim_key not in summary:
            continue
        s = summary[dim_key]
        logger.info(
            f"  {dim_key}: {s['n_finite']} finite + {s['n_infinite']} infinite features, "
            f"total persistence = {s['total_persistence']:.3f}, "
            f"max persistence = {s['max_persistence']:.3f}, "
            f"entropy = {s['persistence_entropy']:.3f}"
        )

    # Betti numbers at representative scales
    logger.info("\nBetti numbers at representative scales:")
    # Use the max death value to set scale range
    max_death = 0
    for dim in ph.dgms:
        finite = ph.dgms[dim][ph.dgms[dim][:, 1] != np.inf]
        if len(finite) > 0:
            max_death = max(max_death, finite[:, 1].max())

    for eps_frac in [0.25, 0.5, 0.75, 1.0]:
        eps = max_death * eps_frac
        betti = ph.betti_at_scale(eps)
        logger.info(f"  ε = {eps:.2f}: β₀={betti.get(0, 0)}, β₁={betti.get(1, 0)}, β₂={betti.get(2, 0)}")

    # Analyze H1 variation
    logger.info("\nH1 Domain Variation Analysis:")
    h1_analysis = analyze_h1_domain_variation(ph, X, domain_names, n_top=5)

    # Save plots
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plot_persistence_diagram(
        ph,
        f"Persistence Diagram — {region.replace('_', ' ').title()} (7D IMD)",
        OUTPUT_DIR / f"pd_{region}.png",
    )
    plot_betti_curves(
        ph,
        f"Betti Curves — {region.replace('_', ' ').title()} (7D IMD)",
        OUTPUT_DIR / f"betti_{region}.png",
    )
    plot_barcode(
        ph,
        f"Persistence Barcode — {region.replace('_', ' ').title()} (7D IMD)",
        OUTPUT_DIR / f"barcode_{region}.png",
    )

    # Permutation test
    perm_results = None
    if do_permutation > 0:
        logger.info(f"\nRunning permutation test ({do_permutation} permutations)...")
        perm_results = permutation_test(
            X,
            n_permutations=do_permutation,
            max_dim=1,  # Test H0 and H1
            statistic="max_persistence",
        )

    elapsed = time.time() - t0

    # Compile results
    results = {
        "region": region,
        "n_lsoas": int(len(X)),
        "n_dimensions": int(X.shape[1]),
        "domain_names": domain_names,
        "elapsed_seconds": elapsed,
        "ripser_time_seconds": ph.elapsed_seconds,
        "persistence_summary": {
            dim_key: {k: v for k, v in s.items() if k != "features"} for dim_key, s in summary.items()
        },
        "top_features": {
            dim_key: [
                {"birth": float(b), "death": float(d), "lifetime": float(lt)}
                for b, d, lt in s.get("features", [])[:10]
                if lt != float("inf")
            ]
            for dim_key, s in summary.items()
        },
        "h1_domain_analysis": h1_analysis,
        "permutation_test": perm_results,
    }

    # Save JSON
    json_path = OUTPUT_DIR / f"multidim_ph_{region}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nResults saved to {json_path}")
    logger.info(f"Total elapsed: {elapsed:.1f}s (ripser: {ph.elapsed_seconds:.1f}s)")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Multidimensional Deprivation Topology (Approach B)",
    )
    parser.add_argument(
        "--region",
        choices=["west_midlands", "greater_manchester"],
        default="west_midlands",
        help="Region to analyze (default: west_midlands)",
    )
    parser.add_argument("--all", action="store_true", help="Run for all regions")
    parser.add_argument(
        "--permutation-test",
        type=int,
        default=0,
        metavar="N",
        help="Run permutation test with N permutations (0 = skip)",
    )
    args = parser.parse_args()

    if args.all:
        for region in ["west_midlands", "greater_manchester"]:
            run_region(region, do_permutation=args.permutation_test)
    else:
        run_region(args.region, do_permutation=args.permutation_test)


if __name__ == "__main__":
    main()
