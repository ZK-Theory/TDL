"""
Phase C1: Residualised PH — Does topology emerge after removing the severity axis?

Usage:
    python -m poverty_tda.validation.run_residualised_ph --region west_midlands
    python -m poverty_tda.validation.run_residualised_ph --all
    python -m poverty_tda.validation.run_residualised_ph --all --permutation-test 50
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.topology.multidim_ph import betti_curve
from poverty_tda.topology.residualised_ph import compute_residualised_ph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "multidim_ph_results"


def plot_comparison_pd(ph_raw, ph_resid, region: str, save_path: Path):
    """Side-by-side persistence diagrams: raw vs residualised."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    for col, (ph, label) in enumerate([(ph_raw, "Raw 7D"), (ph_resid, "Residualised (PC1 removed)")]):
        for row, dim in enumerate([0, 1]):
            ax = axes[row, col]
            color = "#2196F3" if dim == 0 else "#FF5722"
            dim_label = "H₀" if dim == 0 else "H₁"

            if dim in ph.dgms:
                dgm = ph.dgms[dim]
                finite = dgm[dgm[:, 1] != np.inf]
                if len(finite) > 0:
                    births, deaths = finite[:, 0], finite[:, 1]
                    lifetimes = deaths - births
                    max_lt = lifetimes.max() if len(lifetimes) > 0 else 1
                    sizes = np.maximum(10, 80 * lifetimes / max_lt)
                    ax.scatter(births, deaths, c=color, s=sizes, alpha=0.5, edgecolors="white", linewidths=0.3)

            # Diagonal
            all_vals = []
            for d in [0, 1]:
                if d in ph.dgms:
                    f = ph.dgms[d][ph.dgms[d][:, 1] != np.inf]
                    if len(f) > 0:
                        all_vals.extend(f[:, 1].tolist())
            lim = max(all_vals) * 1.05 if all_vals else 1
            ax.plot([0, lim], [0, lim], "k--", alpha=0.3, linewidth=0.5)
            ax.set_xlim(-0.02, lim)
            ax.set_ylim(-0.02, lim)
            ax.set_aspect("equal")
            ax.grid(True, alpha=0.2)

            n_feat = len(ph.dgms[dim][ph.dgms[dim][:, 1] != np.inf]) if dim in ph.dgms else 0
            ax.set_title(f"{label} — {dim_label} ({n_feat} features)", fontsize=11)
            ax.set_xlabel("Birth", fontsize=10)
            ax.set_ylabel("Death", fontsize=10)

    fig.suptitle(f"Raw vs Residualised PH — {region.replace('_', ' ').title()}", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved comparison PD: {save_path}")


def plot_comparison_betti(ph_raw, ph_resid, region: str, save_path: Path):
    """Side-by-side Betti curves: raw vs residualised."""
    curves_raw = betti_curve(ph_raw, n_points=300)
    curves_resid = betti_curve(ph_resid, n_points=300)

    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    colors = {0: "#2196F3", 1: "#FF5722"}
    labels = {0: "β₀", 1: "β₁"}

    for col, (curves, title) in enumerate([(curves_raw, "Raw 7D"), (curves_resid, "Residualised (PC1 removed)")]):
        ax = axes[col]
        for dim in [0, 1]:
            if dim in curves:
                eps, betti = curves[dim]
                if betti.max() > 0:
                    ax.plot(eps, betti, color=colors[dim], label=labels[dim], linewidth=2)
        ax.set_xlabel("Filtration ε", fontsize=12)
        ax.set_ylabel("Betti number", fontsize=12)
        ax.set_title(title, fontsize=12)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.2)
        ax.set_xlim(0, None)
        ax.set_ylim(0, None)

    fig.suptitle(f"Betti Curves — {region.replace('_', ' ').title()}", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved comparison Betti: {save_path}")


def plot_pca_loadings(pca_info: dict, domain_names: list[str], save_path: Path):
    """Bar chart of PC1 loadings (the severity axis)."""
    loadings = pca_info["pc1_loadings"]
    names = list(loadings.keys())
    vals = list(loadings.values())

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(names, vals, color=["#FF5722" if v > 0 else "#2196F3" for v in vals], alpha=0.8, edgecolor="white")
    ax.set_xlabel("PC1 Loading", fontsize=12)
    ax.set_title("PC1 (Severity Axis) — Domain Loadings", fontsize=13, fontweight="bold")
    ax.axvline(0, color="black", linewidth=0.5)
    ax.grid(True, alpha=0.2, axis="x")

    # Annotate variance explained
    ve = pca_info["variance_explained_removed"]
    ax.text(
        0.98,
        0.02,
        f"PC1 explains {ve:.1%} of variance",
        transform=ax.transAxes,
        ha="right",
        fontsize=10,
        style="italic",
    )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved PCA loadings: {save_path}")


def run_c1(region: str, do_permutation: int = 0):
    """Run the full C1 residualised PH analysis for a region."""
    results, ph_raw, ph_resid = compute_residualised_ph(
        region=region,
        n_components_to_remove=1,
        max_dim=1,
        do_permutation=do_permutation,
    )

    # Save plots
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"c1_{region}"

    plot_comparison_pd(ph_raw, ph_resid, region, OUTPUT_DIR / f"pd_comparison_{tag}.png")
    plot_comparison_betti(ph_raw, ph_resid, region, OUTPUT_DIR / f"betti_comparison_{tag}.png")
    plot_pca_loadings(results["pca_info"], results["domain_names"], OUTPUT_DIR / f"pca_loadings_{tag}.png")

    # Save JSON
    json_path = OUTPUT_DIR / f"residualised_ph_{region}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nResults saved to {json_path}")
    logger.info(f"Total elapsed: {results['elapsed_seconds']:.1f}s")

    return results


def main():
    parser = argparse.ArgumentParser(description="Phase C1: Residualised PH")
    parser.add_argument(
        "--region",
        choices=["west_midlands", "greater_manchester"],
        default="west_midlands",
    )
    parser.add_argument("--all", action="store_true", help="Run for both regions")
    parser.add_argument(
        "--permutation-test",
        type=int,
        default=0,
        metavar="N",
        help="Permutation test with N permutations (0 = skip)",
    )
    args = parser.parse_args()

    if args.all:
        for region in ["west_midlands", "greater_manchester"]:
            run_c1(region, do_permutation=args.permutation_test)
    else:
        run_c1(args.region, do_permutation=args.permutation_test)


if __name__ == "__main__":
    main()
