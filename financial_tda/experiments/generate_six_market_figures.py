"""
Generate Six Market Figures
===========================
Generates Magnitude Risk Heatmaps for the expanded 6-asset basket.
Baseline: 2008 GFC Peak (from the 6-market data).
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
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

    # Pre-computed stats or norms?
    # six_market_analysis saves both _norms.csv and _stats.csv
    # But stats.csv is easier if it exists.

    # We saved _stats.csv in the experiment script. Let's use it directly.
    stats_path = DATA_DIR / filename.replace("norms", "stats")
    if stats_path.exists():
        stats = pd.read_csv(stats_path, index_col=0)
        stats.index = pd.to_datetime(stats.index, utc=True)
        if stats.index.tz is not None:
            stats.index = stats.index.tz_localize(None)
        return stats

    # Fallback to norms
    norms_path = DATA_DIR / filename
    if norms_path.exists():
        norms = pd.read_csv(norms_path, index_col=0)
        norms.index = pd.to_datetime(norms.index, utc=True)
        if norms.index.tz is not None:
            norms.index = norms.index.tz_localize(None)
        stats = compute_gk_rolling_statistics(norms, window_size=WINDOW_SIZE)
        return stats.iloc[WINDOW_SIZE:]

    return None


def get_baselines():
    s_08 = load_data("2008_gfc_stats.csv")
    if s_08 is None:
        # Fallback to norms if stats name mismatch
        s_08 = load_data("2008_gfc_norms.csv")

    if s_08 is None:
        return None, None
    return s_08.max(), s_08.min()


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

    # 1. Normalize
    rel_stats = pd.DataFrame(index=stats_df.index)

    # Reordered Columns (L2 Top, L1 Bottom)
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

    # Plot
    plt.figure(figsize=(15, 8))
    cmap, norm = make_traffic_light_cmap()

    matrix = rel_stats.T

    ax = sns.heatmap(
        matrix,
        cmap=cmap,
        norm=norm,
        cbar_kws={"label": "Crisis Intensity (Rel to 6-Market 2008)"},
        yticklabels=[c.replace("_", " ").title() for c in matrix.index],
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

    plt.title(f"Global Basket Risk Heatmap: {title}", fontsize=16)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=300)
    plt.close()
    print(f"Saved {filename}")


def main():
    ensure_dirs()
    b_max, b_min = get_baselines()

    if b_max is None:
        print("Could not load 2008 baseline.")
        return

    # 2008
    s08 = load_data("2008_gfc_stats.csv")
    plot_heatmap(s08, b_max, b_min, "2008 GFC (Global)", "heatmap_global_2008.png")

    # 2023
    s23 = load_data("2023_2025_stats.csv")
    plot_heatmap(s23, b_max, b_min, "2023-2025 (Global Validation)", "heatmap_global_2023.png")

    # 2000
    s00 = load_data("2000_dotcom_stats.csv")
    plot_heatmap(s00, b_max, b_min, "2000 Dotcom (Global)", "heatmap_global_2000.png")

    # 2020
    s20 = load_data("2020_covid_stats.csv")
    plot_heatmap(s20, b_max, b_min, "2020 COVID (Global)", "heatmap_global_2020.png")


if __name__ == "__main__":
    main()
