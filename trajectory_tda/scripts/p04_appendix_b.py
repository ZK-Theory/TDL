"""P04 Appendix B: Hilbert Function and Rank Invariant Analyses.

Computes:
  1. Hilbert function heatmaps (H0, H1) at 10x10 and 20x20 resolution
  2. Rank invariant (H1) — income persistence of topological features
  3. Visualisations: heatmaps, birth/death scatter, income persistence summary

Usage:
    uv run python trajectory_tda/scripts/p04_appendix_b.py
"""

from __future__ import annotations

import json
import logging
import sys
import warnings
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

warnings.filterwarnings("ignore", message=".*KeOps.*")
warnings.filterwarnings("ignore", message=".*pykeops.*")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from trajectory_tda.topology.multipers_bifiltration import (
    FIGURE_DIR,
    RESULTS_DIR,
    auto_rips_radius,
    load_embeddings_and_income,
    maxmin_landmarks,
    run_appendix_b,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

N_LANDMARKS = 2000
RESOLUTIONS = [10, 20]


def plot_hilbert_heatmaps(results: dict, income: np.ndarray) -> None:
    """Plot Hilbert function heatmaps for H0 and H1."""
    fig_dir = FIGURE_DIR / "appendix_b"
    fig_dir.mkdir(parents=True, exist_ok=True)

    for res in RESOLUTIONS:
        key = f"{res}x{res}"
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        for ax_idx, degree in enumerate([0, 1]):
            result = results[f"hilbert_H{degree}_{key}"]
            heatmap = np.array(result.heatmap)
            rips_grid = np.array(result.grid_rips)
            income_grid = np.array(result.grid_income)

            im = axes[ax_idx].imshow(
                heatmap.T,
                origin="lower",
                aspect="auto",
                extent=[rips_grid[0], rips_grid[-1], income_grid[0], income_grid[-1]],
                cmap="RdBu_r",
            )
            axes[ax_idx].set_xlabel("Rips radius (eps)")
            axes[ax_idx].set_ylabel("Income threshold (tau)")
            axes[ax_idx].set_title(
                f"Hilbert H{degree} ({key}) | low_frac={result.low_income_fraction:.3f}"
            )

            # Mark median income
            income_med = float(np.median(income))
            axes[ax_idx].axhline(income_med, color="black", linestyle="--", alpha=0.5)

            plt.colorbar(im, ax=axes[ax_idx], label="Signed weight")

        plt.tight_layout()
        path = fig_dir / f"hilbert_heatmap_{key}.png"
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Saved Hilbert heatmap: %s", path)


def plot_rank_invariant(results: dict, income: np.ndarray) -> None:
    """Plot rank invariant birth/death scatter and income persistence."""
    fig_dir = FIGURE_DIR / "appendix_b"
    fig_dir.mkdir(parents=True, exist_ok=True)

    for res in RESOLUTIONS:
        key = f"{res}x{res}"
        result = results[f"rank_H1_{key}"]
        stats = result.income_persistence_stats

        if result.n_features == 0:
            logger.warning("No rank invariant features for %s", key)
            continue

        birth_tau = np.array(result.birth_income)
        death_tau = np.array(result.death_income)
        weights = np.abs(np.array(result.weights))

        # --- Figure 1: Birth vs Death income scatter ---
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Filter finite deaths for scatter
        finite_mask = np.isfinite(death_tau)
        if np.sum(finite_mask) > 0:
            sc = axes[0].scatter(
                birth_tau[finite_mask],
                death_tau[finite_mask],
                s=weights[finite_mask] * 2,
                c=weights[finite_mask],
                cmap="viridis",
                alpha=0.6,
                edgecolors="none",
            )
            plt.colorbar(sc, ax=axes[0], label="Weight")

        # Diagonal line
        income_med = float(np.median(income))
        lims = [0, income.max() + 0.1]
        axes[0].plot(lims, lims, "k--", alpha=0.3, label="diagonal")
        axes[0].axvline(
            income_med, color="red", linestyle=":", alpha=0.5, label="median"
        )
        axes[0].axhline(income_med, color="red", linestyle=":", alpha=0.5)
        axes[0].set_xlabel("Birth income (tau)")
        axes[0].set_ylabel("Death income (tau)")
        axes[0].set_title(f"Rank Invariant H1 ({key}): Birth vs Death income")
        axes[0].legend(fontsize=8)

        # --- Figure 2: Income persistence summary bar chart ---
        bar_labels = [
            f"Born low\n({stats['n_born_low']})",
            f"Survive to high\n({stats['n_survive_to_high']})",
            f"Confined low\n({stats['n_confined_to_low']})",
            f"Born Q1\n({stats['n_born_q1']})",
            f"Q1->Q3\n({stats['n_survive_q1_to_q3']})",
            f"Persist inf\n({stats['n_persist_to_inf']})",
        ]
        bar_values = [
            stats["frac_born_low"],
            stats["frac_survive_to_high"],
            stats["frac_confined_to_low"],
            stats.get("w_born_q1", 0) / stats["total_weight"]
            if stats["total_weight"] > 0
            else 0,
            stats["frac_q1_surviving_to_q3"],
            stats["frac_persist_to_inf"],
        ]
        colors = ["#2196F3", "#4CAF50", "#FF9800", "#2196F3", "#4CAF50", "#9E9E9E"]

        axes[1].bar(range(len(bar_labels)), bar_values, color=colors, alpha=0.8)
        axes[1].set_xticks(range(len(bar_labels)))
        axes[1].set_xticklabels(bar_labels, fontsize=8)
        axes[1].set_ylabel("Fraction of total weight")
        axes[1].set_title(f"Income Persistence Summary ({key})")
        axes[1].set_ylim(0, 1.05)

        plt.tight_layout()
        path = fig_dir / f"rank_invariant_{key}.png"
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Saved rank invariant figure: %s", path)


def print_summary(results: dict) -> None:
    """Print readable summary of Appendix B results."""
    sep = "=" * 70
    print(f"\n{sep}")
    print("APPENDIX B: HILBERT FUNCTION AND RANK INVARIANT")
    print(sep)

    for res in RESOLUTIONS:
        key = f"{res}x{res}"
        print(f"\n--- Resolution: {key} ---")

        # Hilbert function
        for degree in [0, 1]:
            hf = results[f"hilbert_H{degree}_{key}"]
            print(f"\n  Hilbert H{degree}:")
            print(f"    Total mass: {hf.total_mass:.0f}")
            print(f"    Low-income fraction: {hf.low_income_fraction:.3f}")
            print(f"    Quartile masses: {[f'{m:.0f}' for m in hf.quartile_masses]}")
            print(f"    Compute time: {hf.compute_time_s:.1f}s")

        # Rank invariant
        ri = results[f"rank_H1_{key}"]
        s = ri.income_persistence_stats
        print("\n  Rank Invariant H1:")
        print(f"    Total features: {ri.n_features}")
        print(f"    Total weight: {s['total_weight']:.0f}")
        print(f"    Born at low income: {s['n_born_low']} ({s['frac_born_low']:.3f})")
        print(
            f"    Survive to high income: {s['n_survive_to_high']} "
            f"({s['frac_survive_to_high']:.3f} of born-low)"
        )
        print(
            f"    Confined to low income: {s['n_confined_to_low']} "
            f"({s['frac_confined_to_low']:.3f} of born-low)"
        )
        print(
            f"    Born Q1, survive to Q3: {s['n_survive_q1_to_q3']} "
            f"({s['frac_q1_surviving_to_q3']:.3f} of born-Q1)"
        )
        print(
            f"    Persist to infinity: {s['n_persist_to_inf']} "
            f"({s['frac_persist_to_inf']:.3f})"
        )
        if "mean_income_persistence" in s:
            print(f"    Mean income persistence: {s['mean_income_persistence']:.3f}")
            print(
                f"    Median income persistence: {s['median_income_persistence']:.3f}"
            )
        print(f"    Compute time: {ri.compute_time_s:.1f}s")

    print(f"\n{sep}")


def main() -> None:
    """Run Appendix B analyses."""
    # Load data
    embeddings, income_scores = load_embeddings_and_income()

    # Landmark
    logger.info("Selecting %d maxmin landmarks...", N_LANDMARKS)
    lm_idx = maxmin_landmarks(embeddings, N_LANDMARKS)
    lm_pts = embeddings[lm_idx]
    lm_income = income_scores[lm_idx]

    # Auto Rips radius
    radius = auto_rips_radius(lm_pts)

    # Run Appendix B
    logger.info("Computing Hilbert function and rank invariant...")
    results = run_appendix_b(lm_pts, lm_income, radius, RESOLUTIONS)

    # Plot
    plot_hilbert_heatmaps(results, lm_income)
    plot_rank_invariant(results, lm_income)

    # Print summary
    print_summary(results)

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    save_path = RESULTS_DIR / "p04_appendix_b.json"
    data = {k: asdict(v) for k, v in results.items()}
    with open(save_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info("Results saved to %s", save_path)


if __name__ == "__main__":
    main()
