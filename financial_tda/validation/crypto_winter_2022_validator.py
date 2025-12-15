"""
2022 Crypto Winter Validation Script.

This script validates the TDA crisis detection system on crypto market events:
- Terra/LUNA collapse (May 2022)
- FTX collapse (November 2022)

Key differences from equity validation:
1. Uses Takens embedding approach (single-asset time series)
2. 24/7 market (no weekends/holidays)
3. Higher volatility regime
4. Different crisis dynamics (exchange/protocol failures vs market-wide crashes)
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

from financial_tda.models.change_point_detector import NormalPeriodCalibrator
from financial_tda.topology.embedding import takens_embedding
from financial_tda.topology.filtration import compute_persistence_vr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory
FIGURES_DIR = Path(__file__).parent / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Crypto crisis events
TERRA_LUNA_COLLAPSE = pd.Timestamp("2022-05-09")  # UST depeg starts
FTX_COLLAPSE = pd.Timestamp("2022-11-11")  # FTX bankruptcy filing


def fetch_crypto_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch cryptocurrency data from Yahoo Finance.

    Args:
        ticker: Crypto ticker (e.g., "BTC-USD", "ETH-USD").
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).

    Returns:
        DataFrame with OHLCV data.
    """
    logger.info(f"Fetching {ticker} data from {start_date} to {end_date}...")

    data = yf.download(ticker, start=start_date, end=end_date, progress=False)

    if data.empty:
        raise ValueError(f"No data retrieved for {ticker}")

    logger.info(f"Retrieved {len(data)} days of data")
    return data


def compute_bottleneck_distances_takens(
    prices: pd.Series,
    embedding_dim: int = 3,
    time_delay: int = 1,
    window_size: int = 100,
    stride: int = 1,
) -> pd.Series:
    """
    Compute bottleneck distances using Takens embedding approach.

    Args:
        prices: Price series.
        embedding_dim: Takens embedding dimension (default: 3).
        time_delay: Time delay for embedding (default: 1).
        window_size: Sliding window size (default: 100).
        stride: Stride between windows (default: 1).

    Returns:
        Series of bottleneck distances indexed by date.
    """
    logger.info(
        f"Computing bottleneck distances (Takens embedding: dim={embedding_dim}, "
        f"delay={time_delay}, window={window_size})..."
    )

    # Compute log returns
    returns = np.log(prices / prices.shift(1)).dropna()

    distances = []
    dates = []
    prev_diagram = None

    # Sliding window over returns
    for i in range(0, len(returns) - window_size + 1, stride):
        window_data = returns.iloc[i : i + window_size].values.ravel()  # Ensure 1D
        window_end_date = returns.index[i + window_size - 1]

        # Takens embedding
        embedded = takens_embedding(window_data, delay=time_delay, dimension=embedding_dim)

        # Compute persistence diagram (H1)
        diagram = compute_persistence_vr(embedded, homology_dimensions=(1,))
        h1_diagram = diagram[diagram[:, 2] == 1][:, :2]  # Extract H1 (birth, death)

        if prev_diagram is not None and len(h1_diagram) > 0 and len(prev_diagram) > 0:
            # Compute bottleneck distance
            distance = compute_bottleneck_distance_safe(prev_diagram, h1_diagram)
            distances.append(distance)
            dates.append(window_end_date)

        prev_diagram = h1_diagram

        if (i // stride) % 100 == 0:
            logger.info(f"Processed {i // stride + 1} windows...")

    return pd.Series(distances, index=pd.DatetimeIndex(dates))


def compute_bottleneck_distance_safe(diagram1: np.ndarray, diagram2: np.ndarray) -> float:
    """
    Compute bottleneck distance between two persistence diagrams using persim.

    Uses the persim library which implements the correct bottleneck distance
    algorithm (minimizing maximum matching cost via bipartite matching).

    Args:
        diagram1: First persistence diagram (n_features, 2) with [birth, death].
        diagram2: Second persistence diagram (m_features, 2) with [birth, death].

    Returns:
        Bottleneck distance between the diagrams.

    Raises:
        ImportError: If persim is not installed.
    """
    from persim import bottleneck

    return float(bottleneck(diagram1, diagram2))


def calibrate_threshold(
    distances: pd.Series, crisis_start: pd.Timestamp, percentile: int = 95
) -> tuple[NormalPeriodCalibrator, float]:
    """
    Calibrate detection threshold on pre-crisis normal period.

    Args:
        distances: Bottleneck distance series.
        crisis_start: Start date of crisis.
        percentile: Threshold percentile (default: 95).

    Returns:
        Tuple of (calibrator, threshold).
    """
    logger.info("Calibrating threshold on pre-crisis period...")

    # Pre-crisis normal period
    normal_mask = distances.index < crisis_start
    normal_distances = distances[normal_mask].values

    calibrator = NormalPeriodCalibrator()
    calibrator.fit(normal_distances)

    threshold = calibrator.get_threshold(percentile=percentile)

    logger.info(f"Calibrated: mean={calibrator.mean_:.4f}, std={calibrator.std_:.4f}, " f"threshold={threshold:.4f}")

    return calibrator, threshold


def compute_detection_metrics(
    detections: pd.Series,
    crisis_start: pd.Timestamp,
    crisis_end: pd.Timestamp,
) -> dict:
    """
    Compute detection metrics for crisis event.

    Args:
        detections: Boolean series of detections.
        crisis_start: Crisis start date.
        crisis_end: Crisis end date.

    Returns:
        Dictionary of metrics.
    """
    logger.info("Computing detection metrics...")

    # Lead time
    pre_crisis_detections = detections[detections.index < crisis_start]
    if pre_crisis_detections.any():
        first_detection = pre_crisis_detections[pre_crisis_detections].index[0]
        lead_time_days = (crisis_start - first_detection).days
    else:
        lead_time_days = None

    # Precision/Recall/F1
    crisis_mask = (detections.index >= crisis_start) & (detections.index <= crisis_end)
    crisis_detections = detections[crisis_mask]

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


def plot_crypto_timeline(
    prices: pd.Series,
    distances: pd.Series,
    detections: pd.Series,
    crisis_events: list[tuple[str, pd.Timestamp]],
    threshold: float,
    output_path: Path,
    title: str,
) -> None:
    """
    Plot crypto timeline with prices and bottleneck distances.

    Args:
        prices: Price series.
        distances: Bottleneck distance series.
        detections: Detection series.
        crisis_events: List of (name, date) tuples for crisis events.
        threshold: Detection threshold.
        output_path: Output path for figure.
        title: Plot title.
    """
    logger.info(f"Plotting timeline to {output_path}...")

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    # Plot 1: Price
    ax = axes[0]
    ax.plot(prices.index, prices.values, linewidth=1, color="blue", label="Price")
    for event_name, event_date in crisis_events:
        ax.axvline(event_date, color="red", linestyle="--", linewidth=2, alpha=0.7)
        ax.text(
            event_date,
            ax.get_ylim()[1] * 0.95,
            event_name,
            rotation=90,
            verticalalignment="top",
            fontsize=9,
        )
    ax.set_ylabel("Price (USD)", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(alpha=0.3)

    # Plot 2: Bottleneck Distance
    ax = axes[1]
    ax.plot(
        distances.index,
        distances.values,
        linewidth=1,
        color="green",
        label="Bottleneck Distance",
    )
    ax.axhline(
        threshold,
        color="red",
        linestyle="--",
        linewidth=1.5,
        label="Threshold (95th %ile)",
    )

    # Mark detections
    detection_dates = detections[detections].index
    if len(detection_dates) > 0:
        ax.scatter(
            detection_dates,
            distances.loc[detection_dates],
            color="orange",
            marker="^",
            s=50,
            label="Detections",
            zorder=5,
        )

    for event_name, event_date in crisis_events:
        ax.axvline(event_date, color="red", linestyle="--", linewidth=2, alpha=0.7)

    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Bottleneck Distance", fontsize=11)
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved timeline to {output_path}")


def generate_crypto_report(
    asset_name: str,
    crisis_name: str,
    crisis_date: pd.Timestamp,
    metrics: dict,
    output_path: Path,
) -> None:
    """
    Generate crypto winter validation report.

    Args:
        asset_name: Name of crypto asset.
        crisis_name: Name of crisis event.
        crisis_date: Date of crisis.
        metrics: Detection metrics dictionary.
        output_path: Output path for report.
    """
    logger.info(f"Generating report to {output_path}...")

    lead_status = "✓ PASS" if metrics["lead_time_days"] and metrics["lead_time_days"] >= 5 else "✗ FAIL"
    f1_status = "✓ PASS" if metrics["f1_score"] >= 0.70 else "✗ FAIL"

    report = f"""# 2022 Crypto Winter Validation: {crisis_name}

## Executive Summary

This report validates the TDA crisis detection system on the {crisis_name} using {asset_name} data.

**Key Differences from Equity Markets**:
- Single-asset analysis using Takens embedding (vs multi-index)
- 24/7 trading (no weekends/holidays)
- Higher volatility regime
- Protocol/exchange failure events (vs market-wide crashes)

**Results**:
- **Lead Time**: {metrics["lead_time_days"]} days ({lead_status}, target ≥5 days)
- **Precision**: {metrics["precision"]:.3f}
- **Recall**: {metrics["recall"]:.3f}
- **F1 Score**: {metrics["f1_score"]:.3f} ({f1_status}, target ≥0.70)
- **Total Detections**: {metrics["n_detections"]} ({metrics["n_pre_crisis_detections"]} pre-crisis)

---

## Methodology

### Data Source
- **Asset**: {asset_name}
- **Period**: 2021-01-01 to 2023-06-30
- **Crisis Event**: {crisis_name} ({crisis_date.strftime("%Y-%m-%d")})

### Approach
1. **Embedding**: Takens embedding (dim=3, delay=1) on log-returns
2. **Topology**: H1 persistence diagrams via Vietoris-Rips filtration
3. **Distance**: Bottleneck distance between consecutive diagrams
4. **Threshold**: 95th percentile of pre-crisis normal period

### Key Differences from Equity Validation
- **Single-asset**: No multi-index point cloud (like Gidea & Katz)
- **Takens embedding**: Time-delay reconstruction of attractor
- **Higher frequency**: Daily data but 24/7 market dynamics

---

## Results

### Detection Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Lead Time | {metrics["lead_time_days"]} days | ≥5 days | {lead_status} |
| Precision | {metrics["precision"]:.3f} | - | - |
| Recall | {metrics["recall"]:.3f} | - | - |
| F1 Score | {metrics["f1_score"]:.3f} | ≥0.70 | {f1_status} |

### Detection Timeline
- **First Detection**: {f"{metrics['lead_time_days']} days before crisis" if metrics["n_pre_crisis_detections"] > 0 else "None before crisis"}
- **Total Detections**: {metrics["n_detections"]}
- **Pre-Crisis Detections**: {metrics["n_pre_crisis_detections"]}

---

## Crypto-Specific Observations

### Market Characteristics
- **Volatility**: Crypto markets exhibit significantly higher volatility than equities
- **24/7 Trading**: Continuous price discovery without market closures
- **Event Nature**: {crisis_name} represents protocol/exchange failure rather than market-wide contagion

### Detection System Performance
{"The system successfully detected regime changes well in advance." if metrics["lead_time_days"] and metrics["lead_time_days"] >= 5 else "The system had limited early warning capability."}
{"High precision indicates few false alarms." if metrics["precision"] >= 0.7 else "Lower precision suggests elevated false alarm rate in high-volatility environment."}
{"High recall indicates good coverage of crisis period." if metrics["recall"] >= 0.7 else "Lower recall indicates many crisis days were not detected."}

---

## Comparative Analysis: Crypto vs Equities

### Expected Differences
1. **Higher Baseline Volatility**: Crypto persistence diagrams may show more complexity even in "normal" periods
2. **Rapid Regime Shifts**: Crypto crashes can be faster than equity crashes
3. **Event-Driven**: Exchange/protocol failures vs market-wide stress

### Detection System Adaptability
{"The TDA approach successfully adapted to crypto market dynamics." if metrics["f1_score"] >= 0.60 else "The system faces challenges in the crypto environment, likely due to higher baseline volatility."}

---

## Visualizations

See accompanying figures:
- `{output_path.stem}.png`: Timeline of prices and bottleneck distances with crisis events

---

## Conclusion

{f1_status}: The TDA crisis detection system {"meets" if metrics["f1_score"] >= 0.70 else "does not meet"} success criteria for {crisis_name}.

**Key Takeaways**:
- Takens embedding approach {"effectively captures" if metrics["lead_time_days"] and metrics["lead_time_days"] >= 5 else "struggles to capture"} regime changes in single-asset crypto analysis
- {"System demonstrates robustness across asset classes" if metrics["f1_score"] >= 0.60 else "Crypto markets may require threshold recalibration or alternative features"}
- Lead time of {metrics["lead_time_days"]} days provides {"valuable" if metrics["lead_time_days"] and metrics["lead_time_days"] >= 5 else "limited"} early warning capability

---

*Report generated: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"Saved report to {output_path}")


def main():
    """Run 2022 crypto winter validation."""
    logger.info("=" * 80)
    logger.info("2022 CRYPTO WINTER VALIDATION")
    logger.info("=" * 80)

    # Bitcoin analysis
    logger.info("\n=== BITCOIN ANALYSIS ===")

    btc_data = fetch_crypto_data("BTC-USD", "2021-01-01", "2023-06-30")
    btc_prices = btc_data["Close"]

    # Compute bottleneck distances
    btc_distances = compute_bottleneck_distances_takens(
        btc_prices, embedding_dim=3, time_delay=1, window_size=100, stride=1
    )

    # Terra/LUNA crisis analysis
    logger.info("\n--- Terra/LUNA Collapse ---")
    calibrator_terra, threshold_terra = calibrate_threshold(btc_distances, TERRA_LUNA_COLLAPSE, percentile=95)

    detections_terra = btc_distances > threshold_terra

    # Crisis period: Terra collapse lasted ~2 weeks
    terra_end = TERRA_LUNA_COLLAPSE + pd.Timedelta(days=14)

    metrics_terra = compute_detection_metrics(detections_terra, TERRA_LUNA_COLLAPSE, terra_end)

    # FTX crisis analysis
    logger.info("\n--- FTX Collapse ---")
    calibrator_ftx, threshold_ftx = calibrate_threshold(btc_distances, FTX_COLLAPSE, percentile=95)

    detections_ftx = btc_distances > threshold_ftx

    # Crisis period: FTX collapse was rapid (~1 week)
    ftx_end = FTX_COLLAPSE + pd.Timedelta(days=7)

    metrics_ftx = compute_detection_metrics(detections_ftx, FTX_COLLAPSE, ftx_end)

    # Generate visualizations
    plot_crypto_timeline(
        btc_prices,
        btc_distances,
        detections_terra,
        [("Terra/LUNA", TERRA_LUNA_COLLAPSE), ("FTX", FTX_COLLAPSE)],
        threshold_terra,
        FIGURES_DIR / "crypto_2022_bitcoin_timeline.png",
        "Bitcoin: 2022 Crypto Winter Detection",
    )

    # Generate reports
    generate_crypto_report(
        "Bitcoin (BTC-USD)",
        "Terra/LUNA Collapse",
        TERRA_LUNA_COLLAPSE,
        metrics_terra,
        Path(__file__).parent / "2022_crypto_terra_validation.md",
    )

    generate_crypto_report(
        "Bitcoin (BTC-USD)",
        "FTX Collapse",
        FTX_COLLAPSE,
        metrics_ftx,
        Path(__file__).parent / "2022_crypto_ftx_validation.md",
    )

    logger.info("=" * 80)
    logger.info("CRYPTO WINTER VALIDATION COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
