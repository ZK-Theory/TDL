"""
Phase 10B - Task C.2: Visualize Persistence Evolution
======================================================

Purpose:
    Create visualizations showing how H1 topology evolves during GFC vs COVID.

Input:
    outputs/phase_10b/persistence_diagrams/gfc_2007_2008/
    outputs/phase_10b/persistence_diagrams/covid_2019_2020/

Output:
    outputs/phase_10b/visualizations/gfc_evolution.png
    outputs/phase_10b/visualizations/covid_evolution.png
    outputs/phase_10b/visualizations/comparison.png

Author: Phase 10B Implementation
Date: 2025-12-17
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DIAGRAMS_DIR = BASE_DIR / "outputs" / "phase_10b" / "persistence_diagrams"
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_10b" / "visualizations"

# Crisis configurations
CRISIS_CONFIGS = {
    "gfc_2007_2008": {
        "name": "2008 GFC",
        "crisis_date": "2008-09-15",
        "color": "red",
    },
    "covid_2019_2020": {
        "name": "2020 COVID",
        "crisis_date": "2020-03-23",
        "color": "blue",
    },
}


def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")


def load_summaries():
    """Load diagram summaries for both crises."""
    summaries = {}
    for crisis_id, config in CRISIS_CONFIGS.items():
        summary_file = DIAGRAMS_DIR / crisis_id / "diagram_summary.csv"
        if summary_file.exists():
            df = pd.read_csv(summary_file, index_col=0, parse_dates=True)
            summaries[crisis_id] = df
            print(f"Loaded {crisis_id}: {len(df)} days")
        else:
            print(f"Warning: {summary_file} not found")
    return summaries


def plot_evolution(df, config, output_file):
    """Create evolution plot for a single crisis."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    crisis_date = pd.to_datetime(config["crisis_date"])

    # Plot 1: Number of H1 features
    ax1 = axes[0]
    ax1.plot(df.index, df["n_h1"], color=config["color"], linewidth=1.5)
    ax1.fill_between(df.index, 0, df["n_h1"], alpha=0.3, color=config["color"])
    ax1.axvline(crisis_date, color="black", linestyle="--", linewidth=2, label="Crisis Date")
    ax1.set_ylabel("Number of H1 Features", fontsize=12)
    ax1.set_title(f"{config['name']}: H1 Topology Evolution", fontsize=14, fontweight="bold")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Total H1 persistence
    ax2 = axes[1]
    ax2.plot(df.index, df["h1_total_persistence"], color=config["color"], linewidth=1.5)
    ax2.fill_between(df.index, 0, df["h1_total_persistence"], alpha=0.3, color=config["color"])
    ax2.axvline(crisis_date, color="black", linestyle="--", linewidth=2)
    ax2.set_ylabel("Total H1 Persistence", fontsize=12)
    ax2.grid(True, alpha=0.3)

    # Plot 3: Rolling variance (to show the τ signal source)
    window = 20  # ~1 month
    rolling_var = df["h1_total_persistence"].rolling(window, min_periods=5).var()
    ax3 = axes[2]
    ax3.plot(df.index, rolling_var, color=config["color"], linewidth=1.5)
    ax3.fill_between(df.index, 0, rolling_var, alpha=0.3, color=config["color"])
    ax3.axvline(crisis_date, color="black", linestyle="--", linewidth=2)
    ax3.set_ylabel(f"Rolling Variance ({window}d)", fontsize=12)
    ax3.set_xlabel("Date", fontsize=12)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_file}")


def plot_comparison(summaries):
    """Create side-by-side comparison plot."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    for i, (crisis_id, df) in enumerate(summaries.items()):
        config = CRISIS_CONFIGS[crisis_id]

        # Normalize to days-to-crisis
        crisis_date = pd.to_datetime(config["crisis_date"])
        days_to_crisis = (df.index - crisis_date).days

        # Top row: Total persistence
        ax = axes[0, i]
        ax.plot(days_to_crisis, df["h1_total_persistence"], color=config["color"], linewidth=1.5)
        ax.axvline(0, color="black", linestyle="--", linewidth=2, label="Crisis")
        ax.set_title(f"{config['name']}", fontsize=14, fontweight="bold")
        ax.set_xlabel("Days to Crisis" if i == 0 else "Days from Crisis Start", fontsize=11)
        ax.set_ylabel("Total H1 Persistence", fontsize=11)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Bottom row: Rolling variance
        ax = axes[1, i]
        window = 20
        rolling_var = df["h1_total_persistence"].rolling(window, min_periods=5).var()
        ax.plot(days_to_crisis, rolling_var, color=config["color"], linewidth=1.5)
        ax.axvline(0, color="black", linestyle="--", linewidth=2)
        ax.set_xlabel("Days to Crisis" if i == 0 else "Days from Crisis Start", fontsize=11)
        ax.set_ylabel(f"Rolling Variance ({window}d)", fontsize=11)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Topological Evolution: GFC vs COVID", fontsize=16, fontweight="bold")
    plt.tight_layout()

    output_file = OUTPUT_DIR / "comparison.png"
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_file}")


def plot_overlay(summaries):
    """Create overlay plot comparing both crises on same timeline."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    for crisis_id, df in summaries.items():
        config = CRISIS_CONFIGS[crisis_id]
        crisis_date = pd.to_datetime(config["crisis_date"])

        # Normalize to days-to-crisis
        days_to_crisis = (df.index - crisis_date).days

        # Top: Total persistence
        ax1 = axes[0]
        ax1.plot(days_to_crisis, df["h1_total_persistence"], color=config["color"], linewidth=1.5, label=config["name"])

        # Bottom: Rolling variance
        ax2 = axes[1]
        window = 20
        rolling_var = df["h1_total_persistence"].rolling(window, min_periods=5).var()
        ax2.plot(days_to_crisis, rolling_var, color=config["color"], linewidth=1.5, label=config["name"])

    axes[0].axvline(0, color="black", linestyle="--", linewidth=2, label="Crisis")
    axes[0].set_ylabel("Total H1 Persistence", fontsize=12)
    axes[0].set_title("H1 Persistence: GFC vs COVID (Aligned to Crisis Day)", fontsize=14, fontweight="bold")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].axvline(0, color="black", linestyle="--", linewidth=2)
    axes[1].set_ylabel(f"Rolling Variance ({window}d)", fontsize=12)
    axes[1].set_xlabel("Days Relative to Crisis", fontsize=12)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()

    output_file = OUTPUT_DIR / "overlay_comparison.png"
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_file}")


def main():
    """Main execution."""
    print("=" * 60)
    print("PHASE 10B - TASK C.2: VISUALIZE PERSISTENCE EVOLUTION")
    print("=" * 60)

    ensure_dirs()

    # Load summaries
    summaries = load_summaries()

    if len(summaries) < 2:
        print("Error: Need both crisis summaries to proceed")
        return

    # Create individual plots
    for crisis_id, df in summaries.items():
        config = CRISIS_CONFIGS[crisis_id]
        output_file = OUTPUT_DIR / f"{crisis_id}_evolution.png"
        plot_evolution(df, config, output_file)

    # Create comparison plots
    plot_comparison(summaries)
    plot_overlay(summaries)

    print("\n" + "=" * 60)
    print("TASK C.2 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
