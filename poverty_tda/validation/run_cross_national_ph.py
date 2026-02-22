"""
Phase C3: Cross-National Topology Comparison.

Compares deprivation topology between England and Scotland using
the 5 shared IMD/SIMD domains.

Usage:
    # Full national comparison (subsampled to 2000 per country)
    python -m poverty_tda.validation.run_cross_national_ph

    # Matched city-region comparison: Glasgow vs Birmingham
    python -m poverty_tda.validation.run_cross_national_ph --matched

    # With permutation tests
    python -m poverty_tda.validation.run_cross_national_ph --matched --permutation-test 50
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

from poverty_tda.topology.cross_national_ph import (
    run_cross_national,
)
from poverty_tda.topology.multidim_ph import betti_curve

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "multidim_ph_results"


def plot_cross_national_pd(ph_eng, ph_scot, eng_label, scot_label, save_path: Path):
    """Side-by-side persistence diagrams: England vs Scotland."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    datasets = [(ph_eng, f"England ({eng_label})"), (ph_scot, f"Scotland ({scot_label})")]

    for col, (ph, label) in enumerate(datasets):
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

    fig.suptitle("Cross-National PH Comparison (5 shared domains)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved cross-national PD: {save_path}")


def plot_cross_national_betti(ph_eng, ph_scot, eng_label, scot_label, save_path: Path):
    """Overlaid Betti curves: England vs Scotland."""
    curves_eng = betti_curve(ph_eng, n_points=300)
    curves_scot = betti_curve(ph_scot, n_points=300)

    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    eng_colors = {0: "#2196F3", 1: "#FF5722"}
    scot_colors = {0: "#1565C0", 1: "#D84315"}

    for dim_idx, dim in enumerate([0, 1]):
        ax = axes[dim_idx]
        dim_label = "β₀" if dim == 0 else "β₁"

        if dim in curves_eng:
            eps, betti = curves_eng[dim]
            if betti.max() > 0:
                ax.plot(eps, betti, color=eng_colors[dim], label=f"England {dim_label}", linewidth=2, linestyle="-")
        if dim in curves_scot:
            eps, betti = curves_scot[dim]
            if betti.max() > 0:
                ax.plot(eps, betti, color=scot_colors[dim], label=f"Scotland {dim_label}", linewidth=2, linestyle="--")

        ax.set_xlabel("Filtration ε", fontsize=12)
        ax.set_ylabel(f"Betti number ({dim_label})", fontsize=12)
        ax.set_title(f"{dim_label} Comparison", fontsize=12)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.2)
        ax.set_xlim(0, None)
        ax.set_ylim(0, None)

    fig.suptitle(f"Betti Curves — England ({eng_label}) vs Scotland ({scot_label})", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved cross-national Betti: {save_path}")


def run_comparison(mode: str, do_permutation: int = 0):
    """Run a cross-national comparison."""
    if mode == "matched":
        # Glasgow vs Birmingham (similar large, deprived cities)
        eng_region = "birmingham"
        scot_council = "Glasgow City"
        subsample = None
        tag = "matched_glasgow_vs_birmingham"
    elif mode == "national":
        eng_region = None
        scot_council = None
        subsample = 2000  # Subsample for tractability
        tag = "national"
    else:
        raise ValueError(f"Unknown mode: {mode}")

    results, ph_eng, ph_scot = run_cross_national(
        england_region=eng_region,
        scotland_council=scot_council,
        max_dim=1,
        do_permutation=do_permutation,
        subsample=subsample,
    )

    # Save plots
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eng_label = results["england"]["label"]
    scot_label = results["scotland"]["label"]

    plot_cross_national_pd(ph_eng, ph_scot, eng_label, scot_label, OUTPUT_DIR / f"pd_c3_{tag}.png")
    plot_cross_national_betti(ph_eng, ph_scot, eng_label, scot_label, OUTPUT_DIR / f"betti_c3_{tag}.png")

    # Save JSON
    json_path = OUTPUT_DIR / f"cross_national_{tag}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nResults saved to {json_path}")
    logger.info(f"Total elapsed: {results['elapsed_seconds']:.1f}s")

    return results


def main():
    parser = argparse.ArgumentParser(description="Phase C3: Cross-National PH")
    parser.add_argument("--matched", action="store_true", help="Run matched comparison (Glasgow vs Birmingham)")
    parser.add_argument("--national", action="store_true", help="Run full national comparison (subsampled)")
    parser.add_argument("--all", action="store_true", help="Run both matched and national comparisons")
    parser.add_argument(
        "--permutation-test", type=int, default=0, metavar="N", help="Permutation test with N permutations"
    )
    args = parser.parse_args()

    if args.all:
        run_comparison("matched", do_permutation=args.permutation_test)
        run_comparison("national", do_permutation=args.permutation_test)
    elif args.national:
        run_comparison("national", do_permutation=args.permutation_test)
    else:
        # Default to matched comparison
        run_comparison("matched", do_permutation=args.permutation_test)


if __name__ == "__main__":
    main()
