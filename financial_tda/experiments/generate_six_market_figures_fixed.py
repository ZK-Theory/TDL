"""
Generate Six Market Figures (Fixed Gaps)
========================================
Generates Magnitude Risk Heatmaps for the expanded 6-asset basket.
Fixes "White Patches" by forward-filling small gaps in rolling statistics.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from pathlib import Path
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics

# Configuration
OUTPUT_DIR = Path("figures/six_markets")
DATA_DIR = Path("outputs/six_markets")
WINDOW_SIZE = 500


def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return None

    # Try loading stats first
    stats_path = DATA_DIR / filename.replace("norms", "stats")
    if stats_path.exists():
        stats = pd.read_csv(stats_path, index_col=0)
        stats.index = pd.to_datetime(stats.index, utc=True)
        if stats.index.tz is not None:
            stats.index = stats.index.tz_localize(None)
    else:
        # Compute from norms
        norms = pd.read_csv(DATA_DIR / filename, index_col=0)
        norms.index = pd.to_datetime(norms.index, utc=True)
        if norms.index.tz is not None:
            norms.index = norms.index.tz_localize(None)
        stats = compute_gk_rolling_statistics(norms, window_size=WINDOW_SIZE)
        stats = stats.iloc[WINDOW_SIZE:]

    # FIX GAPS: Forward fill small gaps (up to 5 days) to smooth visual
    # Reindex to daily frquency? No, stock markets have weekends.
    # Just ffill() the existing DataFrame to cover NaNs if they exist within rows?
    # Rolling stats should produce continuous NaNs only at start.
    # If there are NaNs in middle, it means missing data.
    stats = stats.ffill(limit=5)

    return stats


def get_baselines():
    s_08 = load_data("2008_gfc_stats.csv")
    if s_08 is None:
        return None, None
    return s_08.max(), s_08.min()


def make_traffic_light_cmap():
    cmap = mcolors.ListedColormap(["#2ecc71", "#f1c40f", "#e67e22", "#c0392b"])
    bounds = [0.0, 0.5, 0.7, 0.9, 100.0]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)
    return cmap, norm


def normalize_column(series, col_name, baselines_max, baselines_min):
    real_col = col_name if col_name in baselines_max.index else col_name.replace("lag1", "1")
    if real_col not in baselines_max.index:
        return series

    b_max = baselines_max[real_col]
    b_min = baselines_min[real_col]

    if "acf" in col_name.lower():
        safe_floor = 0.80
        if b_max <= safe_floor:
            b_max = 1.0
        norm = (series - safe_floor) / (b_max - safe_floor)
        return norm.clip(0, 1.2)
    else:
        if b_max == 0:
            b_max = 1.0
        return series / b_max


def plot_heatmap(stats_df, baselines_max, baselines_min, title, filename):
    print(f"Generating 6-Market Heatmap: {title}")

    if stats_df.empty:
        return

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

    plt.figure(figsize=(15, 8))
    cmap, norm = make_traffic_light_cmap()
    matrix = rel_stats.T

    ax = plt.gca()
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")

    # Y-axis labels
    ax.set_yticks(np.arange(len(matrix.index)))
    ax.set_yticklabels([c.replace("_", " ").title() for c in matrix.index])

    # Colorbar
    cbar = plt.colorbar(im, ax=ax, ticks=[0.25, 0.6, 0.8, 1.0])
    cbar.ax.set_yticklabels(["Safe", "Warning", "Elevated", "Crisis"])

    tick_step = max(30, len(matrix.columns) // 15)
    date_labels = [d.strftime("%Y-%m-%d") for d in matrix.columns]
    ax.set_xticks(np.arange(0, len(matrix.columns), tick_step))
    ax.set_xticklabels(date_labels[::tick_step], rotation=45, ha="right")

    plt.title(f"Global Basket Risk Heatmap: {title}", fontsize=16)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=300)
    plt.close()
    print(f"Saved {filename}")


def main():
    ensure_dirs()
    b_max, b_min = get_baselines()
    if b_max is None:
        return

    s08 = load_data("2008_gfc_stats.csv")
    plot_heatmap(s08, b_max, b_min, "2008 GFC (Global)", "heatmap_global_2008_fixed.png")

    s23 = load_data("2023_2025_stats.csv")
    plot_heatmap(s23, b_max, b_min, "2023-2025 (Global Validation)", "heatmap_global_2023_fixed.png")

    s00 = load_data("2000_dotcom_stats.csv")
    plot_heatmap(s00, b_max, b_min, "2000 Dotcom (Global)", "heatmap_global_2000_fixed.png")

    s20 = load_data("2020_covid_stats.csv")
    plot_heatmap(s20, b_max, b_min, "2020 COVID (Global)", "heatmap_global_2020_fixed.png")


if __name__ == "__main__":
    main()
