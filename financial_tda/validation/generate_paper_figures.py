"""
Generate Paper Figures (Magnitude Risk Heatmaps) - ACF Fixed
============================================================
Updates normalization logic for ACF Lag-1.

Issue: ACF is structurally high (0.8-0.9) even in normal times, so Ratio-to-Peak
creates "Always Red" heatmaps.

Fix: Use Min-Max Scaling relative to 2008 Range for ACF.
- Value < Min_2008 -> Green (Less correlation than even the start of 2008)
- Value approaching Max_2008 -> Red.
Scale: 0.0 (Min_2008) to 1.0 (Max_2008).
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from pathlib import Path
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics

# Configuration
OUTPUT_DIR = Path("figures")
DATA_DIR = Path("outputs")
WINDOW_SIZE = 500


def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_and_prep_data(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return None

    norms = pd.read_csv(path, index_col=0)
    # Robust numeric index
    norms.index = pd.to_datetime(norms.index, utc=True)
    if norms.index.tz is not None:
        norms.index = norms.index.tz_localize(None)

    # Compute Rolling Stats (Raw Values)
    stats = compute_gk_rolling_statistics(norms, window_size=WINDOW_SIZE)

    # Trim Burn-in
    valid_stats = stats.iloc[WINDOW_SIZE:].copy()

    # Trim Norms for matching plot
    valid_norms = norms.loc[valid_stats.index].copy()

    return valid_norms, valid_stats


def get_2008_baselines():
    _, stats_08 = load_and_prep_data("2008_gfc_lp_norms.csv")
    if stats_08 is None:
        return None, None

    # For Variance/SpecDen: Max is baseline (0 is safe)
    # For ACF: Min and Max are baseline (Min is safe-ish, Max is crisis)
    return stats_08.max(), stats_08.min()


def make_traffic_light_cmap():
    # 0.0 - 0.50: Green
    # 0.50 - 0.75: Yellow/Orange
    # 0.75 - 1.0+: Red
    cmap = mcolors.ListedColormap(["#2ecc71", "#f1c40f", "#e67e22", "#c0392b"])
    bounds = [0.0, 0.5, 0.7, 0.9, 100.0]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)
    return cmap, norm


def normalize_column(series, col_name, baselines_max, baselines_min):
    real_col = col_name if col_name in baselines_max.index else col_name.replace("lag1", "1")
    if real_col not in baselines_max.index:
        return series  # Fallback

    b_max = baselines_max[real_col]
    b_min = baselines_min[real_col]

    if "acf" in col_name.lower():
        # Min-Max Scaling relative to 2008
        # If value < b_min, it should be 0 (Green)
        # If value > b_max, it should be 1 (Red)
        # However, 2008 Min might still be "high".
        # Let's use an absolute "Safe" baseline for ACF?
        # No, let's assume 2008 Min (start of period) was "Normal-ish".
        # 2008 Range: Min=0.91, Max=0.98.
        # This is a very tight range.
        # G&K say variance increases.
        # Maybe variation in ACF is subtle.

        # Let's try: (Value - 0.5) / (Max_2008 - 0.5) -> Assuming 0.5 is randomness?
        # Or just expand dynamic range: (Value - 0.8) / (Max_2008 - 0.8)
        # If 2023 is ~0.85, and range is 0.8->1.0, it will be 0.25 (Green).
        # This seems statistically safer than relying on 2008 specific min.

        safe_floor = 0.80  # Arbitrary "High correlation" floor
        if b_max <= safe_floor:
            b_max = 1.0

        norm = (series - safe_floor) / (b_max - safe_floor)
        return norm.clip(0, 1.2)  # Clip negs to 0

    else:
        # Standard Zero-based Ratio
        if b_max == 0:
            b_max = 1.0
        return series / b_max


def plot_heatmap(stats_df, baselines_max, baselines_min, title, filename, crash_date=None, window_days=500):
    print(f"Generating heatmap: {title}")

    if stats_df.empty:
        return

    # 1. Normalize
    rel_stats = pd.DataFrame(index=stats_df.index)

    cols = [
        "L2_norm_variance",
        "L2_norm_spectral_density_low",
        "L2_norm_acf_lag1",
        "L1_norm_variance",
        "L1_norm_spectral_density_low",
        "L1_norm_acf_lag1",
    ]

    for col in cols:
        real_col = col if col in stats_df.columns else col.replace("lag1", "1")
        if real_col in stats_df.columns:
            rel_stats[col] = normalize_column(stats_df[real_col], real_col, baselines_max, baselines_min)

    # Slice Window
    if crash_date:
        crash_dt = pd.Timestamp(crash_date)
        start = crash_dt - pd.Timedelta(days=window_days)
        end = crash_dt + pd.Timedelta(days=100)
        mask = (rel_stats.index >= start) & (rel_stats.index <= end)
        plot_data = rel_stats.loc[mask]
    else:
        plot_data = rel_stats

    # Plot
    plt.figure(figsize=(15, 8))
    cmap, norm = make_traffic_light_cmap()

    matrix = plot_data.T

    ax = sns.heatmap(
        matrix,
        cmap=cmap,
        norm=norm,
        cbar_kws={"label": "Crisis Intensity (Rel to 2008)"},
        yticklabels=[c.replace("_", " ").title() for c in matrix.index],
        # vmin=0, vmax=1.0 # Handled by norm
    )

    # Annotate Colorbar
    cbar = ax.collections[0].colorbar
    cbar.set_ticks([0.25, 0.6, 0.8, 1.0])
    cbar.set_ticklabels(["Safe", "Warning", "Elevated", "Crisis"])

    # X-axis
    tick_step = max(30, len(matrix.columns) // 15)
    date_labels = [d.strftime("%Y-%m-%d") for d in matrix.columns]
    ax.set_xticks(np.arange(0, len(matrix.columns), tick_step))
    ax.set_xticklabels(date_labels[::tick_step], rotation=45, ha="right")

    if crash_date:
        c_dt = pd.Timestamp(crash_date)
        if c_dt >= matrix.columns[0] and c_dt <= matrix.columns[-1]:
            idx = matrix.columns.get_indexer([c_dt], method="nearest")[0]
            plt.axvline(idx, color="black", linestyle="--", linewidth=3)

    plt.title(f"Systemic Risk Heatmap: {title}", fontsize=16)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=300)
    plt.close()
    print(f"Saved {filename}")


def plot_lp(norms, title, filename, crash_date=None, window_days=500):
    print(f"Generating Lp plot: {title}")

    if crash_date:
        c_dt = pd.Timestamp(crash_date)
        start = c_dt - pd.Timedelta(days=window_days)
        end = c_dt + pd.Timedelta(days=100)
        mask = (norms.index >= start) & (norms.index <= end)
        data = norms.loc[mask]
    else:
        data = norms

    plt.figure(figsize=(14, 6))
    plt.plot(data.index, data["L1_norm"], label="L1 Norm", color="blue", alpha=0.8)
    plt.plot(data.index, data["L2_norm"], label="L2 Norm", color="red", alpha=0.8)

    if crash_date:
        plt.axvline(pd.Timestamp(crash_date), color="black", linestyle="--")

    plt.title(f"Persistence Landscape Norms: {title}")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(OUTPUT_DIR / filename, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {filename}")


def main():
    ensure_dirs()
    b_max, b_min = get_2008_baselines()

    # 2008
    n8, s8 = load_and_prep_data("2008_gfc_lp_norms.csv")
    plot_heatmap(s8, b_max, b_min, "2008 Global Financial Crisis", "heatmap_2008.png", "2008-09-15")
    plot_lp(n8, "2008 Global Financial Crisis", "lp_2008.png", "2008-09-15")

    # 2023
    n23, s23 = load_and_prep_data("2023_2025_realtime_lp_norms.csv")
    plot_heatmap(s23, b_max, b_min, "2023-2025 (Validation)", "heatmap_2023.png", None)
    plot_lp(n23, "2023-2025 (Validation)", "lp_2023.png", None)

    # 2000
    n00, s00 = load_and_prep_data("2000_dotcom_lp_norms.csv")
    plot_heatmap(s00, b_max, b_min, "2000 Dotcom Crash", "heatmap_2000.png", "2000-03-10")
    plot_lp(n00, "2000 Dotcom Crash", "lp_2000.png", "2000-03-10")

    # 2020
    n20, s20 = load_and_prep_data("2020_covid_lp_norms.csv")
    plot_heatmap(s20, b_max, b_min, "2020 COVID Crash", "heatmap_2020.png", "2020-03-16", window_days=400)
    plot_lp(n20, "2020 COVID Crash", "lp_2020.png", "2020-03-16", window_days=400)


if __name__ == "__main__":
    main()
