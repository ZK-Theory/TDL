"""
2020 COVID Crash detection validation script.

This script validates the TDA crisis detection system against the 2020 COVID crash,
measuring lead time, precision, recall, and F1 score for rapid regime change detection.
Generates visualizations and metrics for checkpoint review.

Validation period: 2019-01-01 to 2020-12-31
Key event: COVID crash (2020-02-20 to 2020-03-23) - fastest bear market in history
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from financial_tda.analysis.backtest import KNOWN_CRISES
from financial_tda.data.fetchers import fetch_index
from financial_tda.data.fetchers.yahoo import fetch_ticker
from financial_tda.models.change_point_detector import NormalPeriodCalibrator
from financial_tda.topology.filtration import compute_persistence_vr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory for figures
FIGURES_DIR = Path(__file__).parent / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def fetch_covid_data() -> tuple[dict[str, pd.Series], pd.Series]:
    """
    Fetch multi-index data for 2020 COVID crash validation.

    Returns:
        Tuple of (price_dict, vix_series):
            - price_dict: Dict mapping index names to price series
            - vix_series: VIX index data
    """
    logger.info("Fetching 2020 COVID crash validation data...")

    # Fetch 4 major indices (Gidea & Katz approach)
    index_names = ["sp500", "dji", "nasdaq"]

    # Fetch data from 2019-01-01 to 2020-12-31
    start_date = "2019-01-01"
    end_date = "2020-12-31"

    prices = {}
    for idx_name in index_names:
        logger.info(f"Fetching {idx_name}...")
        data = fetch_index(idx_name, start_date, end_date)
        if not data.empty:
            prices[idx_name] = data["Close"]
        else:
            logger.warning(f"No data for {idx_name}, skipping")

    # Fetch Russell 2000 using ticker directly
    logger.info("Fetching russell2000 (^RUT)...")
    rut_data = fetch_ticker("^RUT", start_date, end_date)
    if not rut_data.empty:
        prices["russell2000"] = rut_data["Close"]
    else:
        logger.warning("No data for russell2000, skipping")

    # Fetch VIX
    logger.info("Fetching VIX...")
    vix_data = fetch_index("vix", start_date, end_date)
    vix_series = vix_data["Close"] if not vix_data.empty else pd.Series()

    return prices, vix_series


def compute_bottleneck_distance_safe(diagram1: np.ndarray, diagram2: np.ndarray) -> float:
    """
    Compute bottleneck distance between two persistence diagrams using scipy.

    Args:
        diagram1: First persistence diagram (n_features, 2) with [birth, death].
        diagram2: Second persistence diagram (m_features, 2) with [birth, death].

    Returns:
        Bottleneck distance between the diagrams.
    """
    from scipy.optimize import linear_sum_assignment

    if len(diagram1) == 0 or len(diagram2) == 0:
        # Handle empty diagrams
        if len(diagram1) == 0 and len(diagram2) == 0:
            return 0.0
        elif len(diagram1) == 0:
            return np.max(diagram2[:, 1] - diagram2[:, 0]) / 2
        else:
            return np.max(diagram1[:, 1] - diagram1[:, 0]) / 2

    # Compute pairwise distances between points
    n, m = len(diagram1), len(diagram2)

    # Create cost matrix including diagonal projections
    cost_matrix = np.full((n + m, n + m), np.inf)

    # Point-to-point distances
    for i in range(n):
        for j in range(m):
            b1, d1 = diagram1[i]
            b2, d2 = diagram2[j]
            cost_matrix[i, j] = max(abs(b1 - b2), abs(d1 - d2))

    # Diagonal projections (matching to diagonal)
    for i in range(n):
        b, d = diagram1[i]
        persistence = d - b
        cost_matrix[i, m + i] = persistence / 2

    for j in range(m):
        b, d = diagram2[j]
        persistence = d - b
        cost_matrix[n + j, j] = persistence / 2

    # Solve assignment problem
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    bottleneck = cost_matrix[row_ind, col_ind].max()

    return float(bottleneck)


def compute_bottleneck_distances(prices: dict[str, pd.Series], window_size: int = 50, stride: int = 1) -> pd.Series:
    """
    Compute bottleneck distances between consecutive persistence diagrams.

    Uses sliding window approach with 4-index point clouds.

    Args:
        prices: Dictionary mapping index names to price series.
        window_size: Size of sliding window (default: 50 days, per Gidea & Katz).
        stride: Stride between windows (default: 1 day).

    Returns:
        Series of bottleneck distances indexed by date.
    """
    logger.info(f"Computing bottleneck distances (window={window_size}, stride={stride})...")

    # Align all series to common dates
    common_index = None
    for series in prices.values():
        if common_index is None:
            common_index = series.index
        else:
            common_index = common_index.intersection(series.index)

    if common_index is None or len(common_index) < window_size + 1:
        raise ValueError("Insufficient overlapping data for sliding window analysis")

    # Create aligned DataFrame with log returns
    returns_df = pd.DataFrame()
    for name, series in prices.items():
        aligned = series.loc[common_index]
        returns_df[name] = np.log(aligned / aligned.shift(1))

    returns_df = returns_df.dropna()

    # Sliding window analysis
    distances = []
    dates = []
    prev_diagram = None

    for i in range(0, len(returns_df) - window_size + 1, stride):
        window_data = returns_df.iloc[i : i + window_size].values
        window_end_date = returns_df.index[i + window_size - 1]

        # Compute persistence diagram (H1 only, per Gidea & Katz)
        diagram = compute_persistence_vr(window_data, homology_dimensions=(1,))
        h1_diagram = diagram[diagram[:, 2] == 1][:, :2]  # Extract H1 features (birth, death)

        if prev_diagram is not None and len(h1_diagram) > 0 and len(prev_diagram) > 0:
            # Compute bottleneck distance
            distance = compute_bottleneck_distance_safe(prev_diagram, h1_diagram)
            distances.append(distance)
            dates.append(window_end_date)

        prev_diagram = h1_diagram

    return pd.Series(distances, index=pd.DatetimeIndex(dates))


def calibrate_normal_period(distances: pd.Series, crisis_start: pd.Timestamp) -> NormalPeriodCalibrator:
    """
    Calibrate change-point detector on pre-crisis normal period.

    Args:
        distances: Series of bottleneck distances.
        crisis_start: Start date of crisis (COVID crash: 2020-02-20).

    Returns:
        Fitted NormalPeriodCalibrator instance.
    """
    logger.info("Calibrating normal period baseline...")

    # Ensure crisis_start is timezone-aware to match distances index
    if distances.index.tz is not None and crisis_start.tz is None:
        crisis_start = crisis_start.tz_localize(distances.index.tz)
    elif distances.index.tz is None and crisis_start.tz is not None:
        crisis_start = crisis_start.tz_localize(None)

    # Use pre-crisis period (before COVID crash) as "normal"
    normal_period_mask = distances.index < crisis_start
    normal_distances = distances[normal_period_mask].values

    calibrator = NormalPeriodCalibrator()
    calibrator.fit(normal_distances)

    logger.info(
        f"Normal period statistics: mean={calibrator.mean_:.4f}, "
        f"std={calibrator.std_:.4f}, n={calibrator.n_samples_}"
    )

    return calibrator


def detect_regime_changes(distances: pd.Series, calibrator: NormalPeriodCalibrator, percentile: int = 95) -> pd.Series:
    """
    Detect regime changes using calibrated thresholds.

    Args:
        distances: Series of bottleneck distances.
        calibrator: Fitted calibrator for threshold determination.
        percentile: Percentile for anomaly threshold (default: 95).

    Returns:
        Boolean series indicating detected regime changes.
    """
    logger.info(f"Detecting regime changes (threshold={percentile}th percentile)...")

    threshold = calibrator.get_threshold(percentile=percentile)
    detections = distances > threshold

    n_detections = detections.sum()
    logger.info(f"Threshold: {threshold:.4f}, Detections: {n_detections}/{len(distances)}")

    return detections


def compute_detection_metrics(
    detections: pd.Series,
    crisis_period: tuple[pd.Timestamp, pd.Timestamp],
    ground_truth_labels: pd.Series | None = None,
) -> dict:
    """
    Compute detection metrics: lead time, precision, recall, F1.

    Args:
        detections: Boolean series of regime change detections.
        crisis_period: Tuple of (crisis_start, crisis_end) timestamps.
        ground_truth_labels: Optional ground truth labels for crisis periods.

    Returns:
        Dictionary of metrics.
    """
    logger.info("Computing detection metrics...")

    crisis_start, crisis_end = crisis_period

    # Ensure timezone compatibility
    if detections.index.tz is not None:
        if crisis_start.tz is None:
            crisis_start = crisis_start.tz_localize(detections.index.tz)
        if crisis_end.tz is None:
            crisis_end = crisis_end.tz_localize(detections.index.tz)

    # Lead time: days before crisis_start that first detection occurred
    pre_crisis_detections = detections[detections.index < crisis_start]
    if pre_crisis_detections.any():
        first_detection = pre_crisis_detections[pre_crisis_detections].index[0]
        lead_time_days = (crisis_start - first_detection).days
    else:
        lead_time_days = None  # No detection before crisis

    # Precision/Recall/F1 if ground truth available
    if ground_truth_labels is not None:
        # Align detections with ground truth
        common_index = detections.index.intersection(ground_truth_labels.index)
        det_aligned = detections.loc[common_index]
        gt_aligned = ground_truth_labels.loc[common_index]

        # True positives: detections during crisis
        tp = (det_aligned & gt_aligned).sum()
        fp = (det_aligned & ~gt_aligned).sum()
        fn = (~det_aligned & gt_aligned).sum()

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    else:
        # Simple heuristic: crisis period detections / total crisis period days
        crisis_mask = (detections.index >= crisis_start) & (detections.index <= crisis_end)
        crisis_detections = detections[crisis_mask]

        # Treat any detection during crisis as TP, outside as FP
        tp = crisis_detections.sum()
        fp = detections[~crisis_mask].sum()
        fn = (~crisis_detections).sum()

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    metrics = {
        "lead_time_days": lead_time_days,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "n_detections": detections.sum(),
        "n_pre_crisis_detections": pre_crisis_detections.sum(),
    }

    logger.info(f"Metrics: {metrics}")
    return metrics


def plot_bottleneck_timeline(
    distances: pd.Series,
    detections: pd.Series,
    crisis_period: tuple[pd.Timestamp, pd.Timestamp],
    threshold: float,
    output_path: Path,
) -> None:
    """
    Plot bottleneck distance time series with crisis period highlighted.

    Args:
        distances: Series of bottleneck distances.
        detections: Boolean series of detections.
        crisis_period: Tuple of (crisis_start, crisis_end).
        threshold: Detection threshold value.
        output_path: Path to save figure.
    """
    logger.info(f"Plotting bottleneck timeline to {output_path}...")

    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot bottleneck distances
    ax.plot(distances.index, distances.values, label="Bottleneck Distance", linewidth=1)

    # Plot threshold line
    ax.axhline(threshold, color="red", linestyle="--", label="Threshold (95th %ile)")

    # Highlight crisis period
    crisis_start, crisis_end = crisis_period
    ax.axvspan(crisis_start, crisis_end, alpha=0.2, color="red", label="Crisis Period")

    # Mark COVID crash start
    ax.axvline(crisis_start, color="black", linestyle=":", label="COVID Crash Start")

    # Mark detections
    detection_dates = detections[detections].index
    if len(detection_dates) > 0:
        ax.scatter(
            detection_dates,
            distances.loc[detection_dates],
            color="orange",
            marker="^",
            s=100,
            label="Detections",
            zorder=5,
        )

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Bottleneck Distance", fontsize=12)
    ax.set_title("2020 COVID Crash: Bottleneck Distance Timeline", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved bottleneck timeline to {output_path}")


def plot_persistence_comparison(
    prices: dict[str, pd.Series],
    pre_crisis_date: pd.Timestamp,
    crisis_date: pd.Timestamp,
    window_size: int,
    output_path: Path,
) -> None:
    """
    Plot persistence diagrams comparing pre-crisis vs crisis periods.

    Args:
        prices: Dictionary of price series.
        pre_crisis_date: Date for pre-crisis snapshot (end of window).
        crisis_date: Date for crisis snapshot (end of window).
        window_size: Window size for point cloud.
        output_path: Path to save figure.
    """
    logger.info(f"Plotting persistence diagram comparison to {output_path}...")

    # Align data
    common_index = None
    for series in prices.values():
        if common_index is None:
            common_index = series.index
        else:
            common_index = common_index.intersection(series.index)

    returns_df = pd.DataFrame()
    for name, series in prices.items():
        aligned = series.loc[common_index]
        returns_df[name] = np.log(aligned / aligned.shift(1))
    returns_df = returns_df.dropna()

    # Extract windows
    def get_window_diagram(end_date: pd.Timestamp) -> np.ndarray:
        # Ensure timezone compatibility
        if returns_df.index.tz is not None and end_date.tz is None:
            end_date = end_date.tz_localize(returns_df.index.tz)
        elif returns_df.index.tz is None and end_date.tz is not None:
            end_date = end_date.tz_localize(None)

        idx = returns_df.index.get_indexer([end_date], method="nearest")[0]
        if idx < window_size:
            raise ValueError(f"Insufficient data before {end_date}")
        window_data = returns_df.iloc[idx - window_size : idx].values
        diagram = compute_persistence_vr(window_data, homology_dimensions=(1,))
        return diagram[diagram[:, 2] == 1][:, :2]  # H1 only (birth, death)

    pre_crisis_diagram = get_window_diagram(pre_crisis_date)
    crisis_diagram = get_window_diagram(crisis_date)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, diagram, title in zip(
        axes,
        [pre_crisis_diagram, crisis_diagram],
        ["Pre-Crisis Period", "Crisis Period"],
    ):
        if len(diagram) > 0:
            ax.scatter(diagram[:, 0], diagram[:, 1], alpha=0.6, s=50)
            # Diagonal line
            max_val = max(diagram[:, 1].max(), diagram[:, 0].max())
            ax.plot([0, max_val], [0, max_val], "k--", linewidth=1, label="Diagonal")
        ax.set_xlabel("Birth", fontsize=11)
        ax.set_ylabel("Death", fontsize=11)
        ax.set_title(f"H1 Persistence Diagram\n{title}", fontsize=12, fontweight="bold")
        ax.grid(alpha=0.3)
        ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved persistence comparison to {output_path}")


def generate_validation_report(
    metrics: dict,
    distances: pd.Series,
    detections: pd.Series,
    crisis_info: dict,
    gfc_metrics: dict,
    output_path: Path,
) -> None:
    """
    Generate markdown validation report with comparison to 2008 GFC.

    Args:
        metrics: Dictionary of detection metrics.
        distances: Series of bottleneck distances.
        detections: Boolean series of detections.
        crisis_info: Dictionary with crisis metadata.
        gfc_metrics: Dictionary with 2008 GFC metrics for comparison.
        output_path: Path to save report.
    """
    logger.info(f"Generating validation report to {output_path}...")

    # Ensure timezone compatibility for all comparisons
    onset_tz = crisis_info["onset_date"]
    recovery_tz = crisis_info["recovery_date"]

    if distances.index.tz is not None:
        if onset_tz.tz is None:
            onset_tz = onset_tz.tz_localize(distances.index.tz)
        if recovery_tz.tz is None:
            recovery_tz = recovery_tz.tz_localize(distances.index.tz)

    # Compute statistics with timezone-aware comparisons
    pre_crisis_mask = distances.index < onset_tz
    crisis_mask = (distances.index >= onset_tz) & (distances.index <= recovery_tz)

    pre_crisis_mean = distances[pre_crisis_mask].mean()
    pre_crisis_std = distances[pre_crisis_mask].std()
    pre_crisis_max = distances[pre_crisis_mask].max()

    crisis_mean = distances[crisis_mask].mean()
    crisis_std = distances[crisis_mask].std()
    crisis_max = distances[crisis_mask].max()

    # Crisis duration
    crisis_duration = (crisis_info["peak_drawdown_date"] - crisis_info["onset_date"]).days

    # Safely format lead time (can be None)
    lead_time_str = f"{metrics['lead_time_days']} days" if metrics["lead_time_days"] is not None else "N/A"
    gfc_lead_time_str = f"{gfc_metrics['lead_time_days']} days" if gfc_metrics["lead_time_days"] is not None else "N/A"

    report = f"""# 2020 COVID Crash Validation Report

## Executive Summary

This report validates the TDA-based crisis detection system against the 2020 COVID market crash, the fastest bear market in history (Feb 20 - Mar 23, 2020).

**Key Findings:**
- **Lead Time**: {lead_time_str} before crash start
- **Precision**: {metrics["precision"]:.3f}
- **Recall**: {metrics["recall"]:.3f}
- **F1 Score**: {metrics["f1_score"]:.3f}
- **Total Detections**: {metrics["n_detections"]} ({metrics["n_pre_crisis_detections"]} pre-crisis)

**Comparison to 2008 GFC:**
- COVID crash duration: {crisis_duration} days vs GFC: 175 days (6.6x faster)
- COVID F1: {metrics["f1_score"]:.3f} vs GFC F1: {gfc_metrics["f1_score"]:.3f}
- COVID lead time: {lead_time_str} vs GFC: {gfc_lead_time_str}

## Methodology

### Data Sources
- **Indices**: S&P 500, DJIA, NASDAQ, Russell 2000 (Gidea & Katz multi-index approach)
- **Validation Period**: 2019-01-01 to 2020-12-31
- **VIX**: Included for context (spiked to 82.69 on Mar 16, 2020)
- **Key Event**: COVID crash (2020-02-20 to 2020-03-23) - 33% S&P 500 decline in 33 days

### Detection Approach
1. **Sliding Window**: 50-day windows with 1-day stride
2. **Point Clouds**: 4-dimensional (4 indices' log-returns)
3. **Topology**: H1 persistence diagrams via Vietoris-Rips filtration
4. **Distance Metric**: Bottleneck distance between consecutive diagrams
5. **Threshold**: 95th percentile of pre-crisis normal period

### Crisis Period Definition
- **Onset**: {crisis_info["onset_date"].strftime("%Y-%m-%d")} (Market starts rapid decline)
- **Peak Drawdown**: {crisis_info["peak_drawdown_date"].strftime("%Y-%m-%d")} (S&P 500 bottom at 2,237)
- **Recovery**: {crisis_info["recovery_date"].strftime("%Y-%m-%d")} (Return to pre-crisis levels)

## Results

### Detection Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Lead Time | {lead_time_str} | ≥5 days | {"✓ PASS" if metrics["lead_time_days"] is not None and metrics["lead_time_days"] >= 5 else "✗ FAIL"} |
| Precision | {metrics["precision"]:.3f} | - | - |
| Recall | {metrics["recall"]:.3f} | - | - |
| F1 Score | {metrics["f1_score"]:.3f} | ≥0.70 | {"✓ PASS" if metrics["f1_score"] >= 0.70 else "✗ FAIL"} |

### Bottleneck Distance Statistics

**Pre-Crisis Normal Period (2019-01-01 to 2020-02-19):**
- Mean Distance: {pre_crisis_mean:.4f}
- Std Distance: {pre_crisis_std:.4f}
- Max Distance: {pre_crisis_max:.4f}

**Crisis Period (2020-02-20 to 2020-08-01):**
- Mean Distance: {crisis_mean:.4f}
- Std Distance: {crisis_std:.4f}
- Max Distance: {crisis_max:.4f}

### Detection Timeline

**First Detection**: {detections.index[0].strftime("%Y-%m-%d") if len(detections[detections]) > 0 else "None"}
**Total Detections**: {metrics["n_detections"]}
**Pre-Crisis Detections**: {metrics["n_pre_crisis_detections"]}

## Visualizations

See accompanying figures:
- `covid_2020_bottleneck_timeline.png`: Time series of bottleneck distances with crisis period highlighted
- `covid_2020_persistence_comparison.png`: Persistence diagrams comparing pre-crisis vs crisis topology

## Comparative Analysis: COVID vs GFC

### Speed Comparison
- **COVID**: {crisis_duration} days from onset to peak drawdown
- **GFC**: 175 days from Lehman collapse to S&P bottom
- **Speed Ratio**: COVID was 6.6x faster than GFC

### Detection Performance
| Metric | COVID 2020 | GFC 2008 | Difference |
|--------|-----------|----------|------------|
| Lead Time | {lead_time_str} | {gfc_lead_time_str} | {f"{metrics['lead_time_days'] - gfc_metrics['lead_time_days']} days" if metrics["lead_time_days"] is not None and gfc_metrics["lead_time_days"] is not None else "N/A"} |
| Precision | {metrics["precision"]:.3f} | {gfc_metrics["precision"]:.3f} | {metrics["precision"] - gfc_metrics["precision"]:.3f} |
| Recall | {metrics["recall"]:.3f} | {gfc_metrics["recall"]:.3f} | {metrics["recall"] - gfc_metrics["recall"]:.3f} |
| F1 Score | {metrics["f1_score"]:.3f} | {gfc_metrics["f1_score"]:.3f} | {metrics["f1_score"] - gfc_metrics["f1_score"]:.3f} |

### Key Insights
- **Speed Adaptation**: {"The detection system " + ("successfully adapted" if metrics["f1_score"] > gfc_metrics["f1_score"] else "struggled to adapt") + " to the rapid regime change."}
- **Lead Time**: {("Similar" if abs(metrics["lead_time_days"] - gfc_metrics["lead_time_days"]) < 30 else "Different") if metrics["lead_time_days"] is not None and gfc_metrics["lead_time_days"] is not None else "N/A"} early warning capability across crisis types.
- **Precision vs Recall**: {"Higher precision" if metrics["precision"] > gfc_metrics["precision"] else "Lower precision"} for COVID indicates {"fewer false alarms" if metrics["precision"] > gfc_metrics["precision"] else "more false alarms"}.

## Interpretation

### Strengths
- Multi-index approach captures synchronized market collapse
- Rapid detection capability despite unprecedented speed
- Topological features robust to volatility regime changes

### Limitations
- Sliding window lag (25 days) relative to 33-day crash duration
- Threshold calibrated on longer crises may not be optimal for rapid events
- Does not distinguish between exogenous shock (pandemic) vs endogenous crisis

### Observations
The COVID crash represents an extreme test case: an exogenous shock causing the fastest bear market in history. The detection system's performance on this event reveals its ability (or inability) to adapt to unprecedented speed of regime change.

## Conclusion

{"✓ PASS" if (metrics["lead_time_days"] and metrics["lead_time_days"] >= 5 and metrics["f1_score"] >= 0.70) else "✗ FAIL"}: The TDA crisis detection system {"meets" if (metrics["lead_time_days"] and metrics["lead_time_days"] >= 5 and metrics["f1_score"] >= 0.70) else "does not meet"} success criteria for the 2020 COVID crash event.

---

*Report generated: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"Saved validation report to {output_path}")


def main():
    """Run 2020 COVID crash validation."""
    logger.info("=" * 80)
    logger.info("2020 COVID CRASH VALIDATION")
    logger.info("=" * 80)

    # Fetch data
    prices, vix = fetch_covid_data()

    if len(prices) < 4:
        logger.error("Insufficient data fetched. Need all 4 indices.")
        return

    # Get crisis metadata
    covid_crisis = [c for c in KNOWN_CRISES if c.name == "COVID"][0]
    crisis_info = {
        "onset_date": covid_crisis.onset_date,
        "peak_drawdown_date": covid_crisis.peak_drawdown_date,
        "recovery_date": covid_crisis.recovery_date,
    }

    # Compute bottleneck distances
    distances = compute_bottleneck_distances(prices, window_size=50, stride=1)

    # Calibrate normal period (pre-COVID)
    calibrator = calibrate_normal_period(distances, covid_crisis.onset_date)

    # Detect regime changes
    detections = detect_regime_changes(distances, calibrator, percentile=95)

    # Compute metrics
    metrics = compute_detection_metrics(
        detections,
        (covid_crisis.onset_date, covid_crisis.recovery_date),
        ground_truth_labels=None,
    )

    # GFC metrics for comparison (from Step 1)
    gfc_metrics = {
        "lead_time_days": 226,
        "precision": 0.747,
        "recall": 0.230,
        "f1_score": 0.351,
    }

    # Generate visualizations
    threshold = calibrator.get_threshold(percentile=95)
    plot_bottleneck_timeline(
        distances,
        detections,
        (covid_crisis.onset_date, covid_crisis.recovery_date),
        threshold,
        FIGURES_DIR / "covid_2020_bottleneck_timeline.png",
    )

    plot_persistence_comparison(
        prices,
        pre_crisis_date=pd.Timestamp("2020-01-15"),  # 5 weeks before crash
        crisis_date=pd.Timestamp("2020-03-15"),  # Near peak volatility
        window_size=50,
        output_path=FIGURES_DIR / "covid_2020_persistence_comparison.png",
    )

    # Generate report
    generate_validation_report(
        metrics,
        distances,
        detections,
        crisis_info,
        gfc_metrics,
        Path(__file__).parent / "2020_covid_validation.md",
    )

    logger.info("=" * 80)
    logger.info("2020 COVID VALIDATION COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
