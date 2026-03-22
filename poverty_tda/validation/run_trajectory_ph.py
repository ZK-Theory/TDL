"""
Phase C2: Longitudinal Trajectory PH on Scotland.

Usage:
    python -m poverty_tda.validation.run_trajectory_ph
    python -m poverty_tda.validation.run_trajectory_ph --council glasgow
    python -m poverty_tda.validation.run_trajectory_ph --all --permutation-test 50
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
from poverty_tda.topology.trajectory_ph import run_trajectory_ph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "multidim_ph_results"


def plot_trajectory_comparison(ph_dict, council_label: str, save_path: Path):
    """3-panel persistence diagram: static vs displacement vs concatenated."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    titles = {
        "static_2020": "Static 2020 (7D)",
        "displacement": "Displacement Δ (7D)",
        "concatenated": "Concat [2016,2020] (14D)",
    }

    for col, key in enumerate(["static_2020", "displacement", "concatenated"]):
        ax = axes[col]
        ph = ph_dict[key]

        for dim in [0, 1]:
            color = "#2196F3" if dim == 0 else "#FF5722"
            label = "H₀" if dim == 0 else "H₁"
            if dim in ph.dgms:
                dgm = ph.dgms[dim]
                finite = dgm[dgm[:, 1] != np.inf]
                if len(finite) > 0:
                    births, deaths = finite[:, 0], finite[:, 1]
                    lifetimes = deaths - births
                    max_lt = lifetimes.max() if len(lifetimes) > 0 else 1
                    sizes = np.maximum(8, 60 * lifetimes / max_lt)
                    ax.scatter(
                        births, deaths, c=color, s=sizes, alpha=0.5, edgecolors="white", linewidths=0.3, label=label
                    )

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
        ax.set_title(titles[key], fontsize=12)
        ax.set_xlabel("Birth", fontsize=10)
        ax.set_ylabel("Death", fontsize=10)
        ax.legend(fontsize=9)

    fig.suptitle(f"Trajectory PH — Scotland ({council_label})", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved trajectory PD: {save_path}")


def plot_trajectory_betti(ph_dict, council_label: str, save_path: Path):
    """3-panel Betti curves: static vs displacement vs concatenated."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    titles = {
        "static_2020": "Static 2020",
        "displacement": "Displacement Δ",
        "concatenated": "Concat [2016,2020]",
    }
    colors = {0: "#2196F3", 1: "#FF5722"}
    labels = {0: "β₀", 1: "β₁"}

    for col, key in enumerate(["static_2020", "displacement", "concatenated"]):
        ax = axes[col]
        ph = ph_dict[key]
        curves = betti_curve(ph, n_points=300)

        for dim in [0, 1]:
            if dim in curves:
                eps, betti = curves[dim]
                if betti.max() > 0:
                    ax.plot(eps, betti, color=colors[dim], label=labels[dim], linewidth=2)

        ax.set_xlabel("Filtration ε", fontsize=11)
        ax.set_ylabel("Betti number", fontsize=11)
        ax.set_title(titles[key], fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.2)
        ax.set_xlim(0, None)
        ax.set_ylim(0, None)

    fig.suptitle(f"Trajectory Betti Curves — Scotland ({council_label})", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved trajectory Betti: {save_path}")


def run_c2(council: str | None, do_permutation: int = 0):
    """Run the full C2 trajectory PH analysis."""
    results, ph_dict = run_trajectory_ph(
        council=council,
        max_dim=1,
        do_permutation=do_permutation,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"c2_{council or 'all_scotland'}"

    plot_trajectory_comparison(ph_dict, council or "all Scotland", OUTPUT_DIR / f"pd_{tag}.png")
    plot_trajectory_betti(ph_dict, council or "all Scotland", OUTPUT_DIR / f"betti_{tag}.png")

    json_path = OUTPUT_DIR / f"trajectory_ph_{council or 'all_scotland'}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nResults saved to {json_path}")
    logger.info(f"Total elapsed: {results['elapsed_seconds']:.1f}s")

    return results


def main():
    parser = argparse.ArgumentParser(description="Phase C2: Trajectory PH")
    parser.add_argument("--council", default=None, help="Council area or region key (e.g. 'glasgow', 'Glasgow City')")
    parser.add_argument("--all", action="store_true", help="Run for both Glasgow and all Scotland")
    parser.add_argument("--permutation-test", type=int, default=0, metavar="N")
    args = parser.parse_args()

    if args.all:
        run_c2("glasgow", do_permutation=args.permutation_test)
        run_c2(None, do_permutation=args.permutation_test)
    else:
        run_c2(args.council or "glasgow", do_permutation=args.permutation_test)


if __name__ == "__main__":
    main()
