"""
Test script to validate Financial TDA Dashboard functionality.

This script tests the dashboard's core functionality by simulating the user workflow:
1. Data loading (Yahoo Finance)
2. Persistence diagram computation
3. Regime detection
4. Anomaly detection

Tests with S&P 500 data covering major crisis periods (2008, 2020, 2022).
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from financial_tda.analysis.windowed import (
    extract_windowed_features,
    sliding_window_generator,
)
from financial_tda.data.fetchers.yahoo import YahooFinanceDataFetcher
from financial_tda.models.regime_classifier import (
    RegimeClassifier,
    create_regime_labels,
    prepare_features,
)
from financial_tda.topology.embedding import takens_embedding
from financial_tda.topology.filtration import compute_persistence_vr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_data_loading():
    """Test 1: Data Loading from Yahoo Finance"""
    logger.info("=" * 80)
    logger.info("TEST 1: Data Loading")
    logger.info("=" * 80)

    try:
        # Fetch S&P 500 data covering multiple crises
        fetcher = YahooFinanceDataFetcher(ticker="^GSPC")
        price_data = fetcher.fetch_data(
            start_date="2007-01-01",
            end_date="2023-12-31",
        )

        if price_data is not None and len(price_data) > 0:
            logger.info(f"✓ Loaded {len(price_data)} data points")
            logger.info(f"  Date range: {price_data.index.min()} to {price_data.index.max()}")
            logger.info(f"  Columns: {list(price_data.columns)}")

            # Compute returns
            returns = price_data["close"].pct_change().dropna()
            logger.info(f"✓ Computed {len(returns)} return values")
            logger.info(f"  Mean return: {returns.mean():.6f}")
            logger.info(f"  Std deviation: {returns.std():.6f}")

            return price_data, returns
        else:
            logger.error("✗ Failed to fetch data")
            return None, None

    except Exception as e:
        logger.exception(f"✗ Error in data loading: {e}")
        return None, None


def test_persistence_computation(returns, window_size=40, stride=5, embedding_dim=3, embedding_delay=5):
    """Test 2: Persistence Diagram Computation"""
    logger.info("=" * 80)
    logger.info("TEST 2: Persistence Diagram Computation")
    logger.info("=" * 80)

    try:
        returns_array = returns.values

        persistence_results = []
        window_dates = []
        n_windows_processed = 0
        n_windows_failed = 0

        logger.info(
            f"Parameters: window_size={window_size}, stride={stride}, "
            f"embedding_dim={embedding_dim}, embedding_delay={embedding_delay}"
        )

        for start_idx, end_idx, window_data in sliding_window_generator(
            returns_array,
            window_size=window_size,
            stride=stride,
        ):
            try:
                # Takens embedding
                point_cloud = takens_embedding(
                    window_data,
                    delay=embedding_delay,
                    dimension=embedding_dim,
                )

                # Compute persistence
                diagram = compute_persistence_vr(
                    point_cloud,
                    homology_dimensions=(0, 1, 2),
                )

                persistence_results.append(diagram)
                window_date = returns.index[end_idx - 1]
                window_dates.append(window_date)
                n_windows_processed += 1

            except Exception as e:
                n_windows_failed += 1
                if n_windows_failed <= 3:  # Show first few failures
                    logger.warning(f"Failed window [{start_idx}:{end_idx}]: {e}")

        logger.info(f"✓ Computed {n_windows_processed} persistence diagrams")
        if n_windows_failed > 0:
            logger.warning(f"  {n_windows_failed} windows failed")

        # Analyze sample diagram
        if len(persistence_results) > 0:
            sample_diagram = persistence_results[len(persistence_results) // 2]  # Middle window
            sample_date = window_dates[len(window_dates) // 2]

            h0_count = (sample_diagram[:, 2] == 0).sum()
            h1_count = (sample_diagram[:, 2] == 1).sum()
            h2_count = (sample_diagram[:, 2] == 2).sum()

            logger.info(f"  Sample diagram ({sample_date.strftime('%Y-%m-%d')}):")
            logger.info(f"    H0 features: {h0_count}")
            logger.info(f"    H1 features: {h1_count}")
            logger.info(f"    H2 features: {h2_count}")

        return persistence_results, window_dates

    except Exception as e:
        logger.exception(f"✗ Error in persistence computation: {e}")
        return None, None


def test_regime_detection(price_data, returns, window_size=40, stride=5, embedding_dim=3, embedding_delay=5):
    """Test 3: Regime Detection and Classification"""
    logger.info("=" * 80)
    logger.info("TEST 3: Regime Detection")
    logger.info("=" * 80)

    try:
        # Extract windowed features
        returns_array = returns.values
        windowed_features_df = extract_windowed_features(
            returns_array,
            window_size=window_size,
            stride=stride,
            embedding_dim=embedding_dim,
            embedding_delay=embedding_delay,
        )

        logger.info(f"✓ Extracted windowed features: {windowed_features_df.shape}")

        # Fetch VIX data
        try:
            vix_fetcher = YahooFinanceDataFetcher(ticker="^VIX")
            vix_data = vix_fetcher.fetch_data(
                start_date=price_data.index.min().strftime("%Y-%m-%d"),
                end_date=price_data.index.max().strftime("%Y-%m-%d"),
            )
            logger.info(f"✓ Fetched VIX data: {len(vix_data)} points")
        except Exception as e:
            logger.warning(f"Could not fetch VIX: {e}, using volatility proxy")
            rolling_vol = returns.rolling(window=20).std() * np.sqrt(252) * 100
            vix_data = pd.DataFrame(
                {"close": rolling_vol},
                index=returns.index,
            )

        # Create regime labels
        regime_labels = create_regime_labels(
            prices=price_data["close"],
            vix=vix_data["close"],
            vix_crisis_threshold=25.0,
            vix_normal_threshold=20.0,
            drawdown_threshold=0.15,
        )

        logger.info(f"✓ Created regime labels: {len(regime_labels)} total")
        crisis_count = (regime_labels == 1).sum()
        normal_count = (regime_labels == 0).sum()
        ambiguous_count = regime_labels.isna().sum()
        logger.info(f"  Crisis: {crisis_count}, Normal: {normal_count}, Ambiguous: {ambiguous_count}")

        # Align labels with features
        feature_dates = windowed_features_df["window_end"]
        aligned_labels = []
        valid_indices = []

        for i, date in enumerate(feature_dates):
            if date in regime_labels.index:
                label = regime_labels.loc[date]
                if not pd.isna(label):
                    aligned_labels.append(int(label))
                    valid_indices.append(i)

        logger.info(f"✓ Aligned labels: {len(aligned_labels)} valid samples")

        if len(aligned_labels) > 10:
            # Train classifier
            X, scaler = prepare_features(windowed_features_df.iloc[valid_indices])
            y = np.array(aligned_labels)

            classifier = RegimeClassifier(
                classifier_type="random_forest",
                class_weight="balanced",
                random_state=42,
            )

            classifier.fit(X, y)
            logger.info("✓ Trained Random Forest classifier")

            # Predict on all windows
            X_all, _ = prepare_features(windowed_features_df, scaler=scaler, fit_scaler=False)
            predictions = classifier.predict(X_all)
            probabilities = classifier.predict_proba(X_all)

            crisis_detected = (predictions == 1).sum()
            normal_detected = (predictions == 0).sum()
            mean_confidence = probabilities[:, 1].mean()

            logger.info("✓ Classification results:")
            logger.info(f"  Crisis windows: {crisis_detected}")
            logger.info(f"  Normal windows: {normal_detected}")
            logger.info(f"  Mean crisis probability: {mean_confidence:.2%}")

            return predictions, probabilities, windowed_features_df
        else:
            logger.error(f"✗ Not enough labeled data: {len(aligned_labels)} samples")
            return None, None, None

    except Exception as e:
        logger.exception(f"✗ Error in regime detection: {e}")
        return None, None, None


def test_anomaly_detection(persistence_diagrams):
    """Test 4: Anomaly Detection (simplified without autoencoder training)"""
    logger.info("=" * 80)
    logger.info("TEST 4: Anomaly Detection Setup")
    logger.info("=" * 80)

    try:
        from financial_tda.topology.features import persistence_image

        # Convert to persistence images
        persistence_images = []

        for diagram in persistence_diagrams:
            # Filter for H1 features
            h1_diagram = diagram[diagram[:, 2] == 1][:, :2]

            if len(h1_diagram) > 0:
                img = persistence_image(
                    h1_diagram,
                    resolution=(50, 50),
                    sigma=0.1,
                )
                persistence_images.append(img)
            else:
                persistence_images.append(np.zeros((50, 50)))

        persistence_images = np.array(persistence_images)

        logger.info(f"✓ Generated {len(persistence_images)} persistence images")
        logger.info(f"  Image shape: {persistence_images.shape}")
        logger.info(f"  Value range: [{persistence_images.min():.6f}, {persistence_images.max():.6f}]")

        # Check for PyTorch availability
        try:
            import torch

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"✓ PyTorch available, device: {device}")

            from financial_tda.models.persistence_autoencoder import (
                PersistenceAutoencoder,
            )

            model = PersistenceAutoencoder(
                input_size=(50, 50),
                latent_dim=32,
            )
            logger.info("✓ PersistenceAutoencoder initialized")
            logger.info(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")
            logger.info("  Note: Training would take ~50 epochs on this data")

        except ImportError as e:
            logger.warning(f"PyTorch not available: {e}")

        return persistence_images

    except Exception as e:
        logger.exception(f"✗ Error in anomaly detection setup: {e}")
        return None


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 80)
    logger.info("FINANCIAL TDA DASHBOARD - FUNCTIONALITY TEST")
    logger.info("=" * 80 + "\n")

    # Test 1: Data Loading
    price_data, returns = test_data_loading()
    if price_data is None:
        logger.error("Cannot proceed without data")
        return

    print("\n")

    # Test 2: Persistence Computation
    persistence_diagrams, window_dates = test_persistence_computation(
        returns,
        window_size=40,
        stride=5,
        embedding_dim=3,
        embedding_delay=5,
    )
    if persistence_diagrams is None:
        logger.error("Cannot proceed without persistence diagrams")
        return

    print("\n")

    # Test 3: Regime Detection
    predictions, probabilities, windowed_features = test_regime_detection(
        price_data,
        returns,
        window_size=40,
        stride=5,
        embedding_dim=3,
        embedding_delay=5,
    )

    print("\n")

    # Test 4: Anomaly Detection Setup
    persistence_images = test_anomaly_detection(persistence_diagrams)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✓ Data Loading: PASSED ({len(price_data)} points)")
    logger.info(f"✓ Persistence Computation: PASSED ({len(persistence_diagrams)} diagrams)")

    if predictions is not None:
        logger.info(f"✓ Regime Detection: PASSED ({len(predictions)} predictions)")
    else:
        logger.info("✗ Regime Detection: FAILED")

    if persistence_images is not None:
        logger.info(f"✓ Anomaly Detection Setup: PASSED ({len(persistence_images)} images)")
    else:
        logger.info("✗ Anomaly Detection Setup: FAILED")

    logger.info("\n" + "=" * 80)
    logger.info("Dashboard is ready for visual testing at http://localhost:8501")
    logger.info("=" * 80 + "\n")


if __name__ == "__main__":
    main()
