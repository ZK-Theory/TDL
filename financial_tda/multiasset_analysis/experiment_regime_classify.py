"""
Multi-Asset TDA: Experiment B - Regime Classification
Uses TDA features to classify market regimes (Normal / Risk-Off / Liquidity Crisis).

This is the most ambitious part of Project B:
- Trains a classifier on TDA-derived features
- Tests if we can distinguish "healthy de-risking" from "panic liquidation"
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from typing import Dict, List, Tuple

# Local imports
from fetch_multiasset_data import MultiAssetDataFetcher
from tda_analysis import rolling_tda_analysis, extract_regime_features

# =============================================================================
# REGIME DEFINITIONS
# =============================================================================


class MarketRegime:
    """Enum-like class for market regimes."""

    NORMAL = 0
    RISK_OFF = 1
    LIQUIDITY_CRISIS = 2
    RECOVERY = 3


REGIME_NAMES = {
    MarketRegime.NORMAL: "Normal",
    MarketRegime.RISK_OFF: "Risk-Off",
    MarketRegime.LIQUIDITY_CRISIS: "Liquidity Crisis",
    MarketRegime.RECOVERY: "Recovery",
}

# Manual labeling of known periods
# Format: (start_date, end_date, regime)
LABELED_PERIODS = [
    # 2008 GFC was Risk-Off (flight to safety worked initially)
    ("2008-09-01", "2008-10-15", MarketRegime.RISK_OFF),
    ("2008-10-16", "2008-11-30", MarketRegime.LIQUIDITY_CRISIS),  # Deleveraging phase
    # 2011 Debt Ceiling - Classic Risk-Off
    ("2011-07-15", "2011-08-15", MarketRegime.RISK_OFF),
    # 2020 COVID - Initially Risk-Off, then Liquidity Crisis
    ("2020-02-20", "2020-03-09", MarketRegime.RISK_OFF),
    ("2020-03-10", "2020-03-23", MarketRegime.LIQUIDITY_CRISIS),  # "Everything sells off"
    ("2020-03-24", "2020-04-30", MarketRegime.RECOVERY),
    # 2022 Rate Shock - Prolonged duration pain (not liquidity)
    ("2022-01-01", "2022-06-30", MarketRegime.RISK_OFF),
    ("2022-09-01", "2022-10-31", MarketRegime.RISK_OFF),
]


# =============================================================================
# LABELING UTILITIES
# =============================================================================


def label_data(features: pd.DataFrame, labeled_periods: List[Tuple[str, str, int]] = LABELED_PERIODS) -> pd.DataFrame:
    """
    Assign regime labels to feature data based on known periods.

    Unlabeled periods default to NORMAL (0).
    """
    labels = pd.Series(MarketRegime.NORMAL, index=features.index, name="Regime")

    for start, end, regime in labeled_periods:
        mask = (features.index >= start) & (features.index <= end)
        labels.loc[mask] = regime

    return pd.concat([features, labels], axis=1)


def balance_classes(data: pd.DataFrame, target_col: str = "Regime", undersampling_ratio: float = 0.5) -> pd.DataFrame:
    """
    Balance classes by undersampling the majority class (NORMAL).

    Args:
        data: DataFrame with features and target
        target_col: Name of target column
        undersampling_ratio: Ratio of NORMAL samples to keep (1.0 = no undersampling)

    Returns:
        Balanced DataFrame
    """
    normal = data[data[target_col] == MarketRegime.NORMAL]
    other = data[data[target_col] != MarketRegime.NORMAL]

    # Undersample normal
    n_keep = int(len(normal) * undersampling_ratio)
    normal_sampled = normal.sample(n=n_keep, random_state=42)

    return pd.concat([normal_sampled, other]).sort_index()


# =============================================================================
# CLASSIFIER PIPELINE
# =============================================================================


class RegimeClassifier:
    """
    Trains and evaluates classifiers on TDA-derived features.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.model = None
        self.feature_cols = None

    def prepare_data(self, data: pd.DataFrame, target_col: str = "Regime") -> Tuple[np.ndarray, np.ndarray]:
        """Split features and target, scale features."""
        self.feature_cols = [c for c in data.columns if c != target_col]
        X = data[self.feature_cols].values
        y = data[target_col].values
        return X, y

    def train(self, data: pd.DataFrame, model_type: str = "random_forest", test_size: float = 0.2) -> Dict:
        """
        Train classifier with cross-validation.

        Args:
            data: Labeled DataFrame from label_data()
            model_type: 'logistic' or 'random_forest'
            test_size: Fraction for holdout test

        Returns:
            Dictionary with metrics
        """
        X, y = self.prepare_data(data)

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42, stratify=y)

        # Scale
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Model selection
        if model_type == "logistic":
            self.model = LogisticRegression(max_iter=1000, class_weight="balanced", multi_class="multinomial")
        else:
            self.model = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)

        # Train
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test_scaled)

        # Cross-validation on full data
        cv_scores = cross_val_score(self.model, self.scaler.fit_transform(X), y, cv=5, scoring="f1_weighted")

        results = {
            "test_accuracy": (y_pred == y_test).mean(),
            "cv_f1_mean": cv_scores.mean(),
            "cv_f1_std": cv_scores.std(),
            "classification_report": classification_report(
                y_test, y_pred, target_names=[REGIME_NAMES[i] for i in sorted(set(y_test))]
            ),
            "confusion_matrix": confusion_matrix(y_test, y_pred),
        }

        return results

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Predict regime for new data."""
        if self.model is None:
            raise ValueError("Model not trained")
        X = features[self.feature_cols].values
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def get_feature_importance(self) -> pd.Series:
        """Get feature importance (for Random Forest)."""
        if hasattr(self.model, "feature_importances_"):
            return pd.Series(self.model.feature_importances_, index=self.feature_cols).sort_values(ascending=False)
        return None


# =============================================================================
# MAIN EXPERIMENT
# =============================================================================


def run_experiment_b(
    config_name: str = "extended", model_type: str = "random_forest", save_results: bool = True
) -> Dict:
    """
    Run Experiment B: Regime Classification.

    Pipeline:
    1. Fetch data and compute TDA features
    2. Label known regimes
    3. Train classifier
    4. Evaluate and report
    """
    print("=" * 70)
    print(f"EXPERIMENT B: REGIME CLASSIFICATION ({config_name.upper()})")
    print("=" * 70)

    output_dir = "../outputs/multiasset/exp_b_regime"
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Fetch and compute TDA
    print("\n[1/4] Fetching data...")
    fetcher = MultiAssetDataFetcher(config=config_name)
    data = fetcher.fetch_and_align(standardize=True)

    print("\n[2/4] Computing TDA features...")
    norms = rolling_tda_analysis(data, verbose=True)
    features = extract_regime_features(norms, window_size=60)

    # Step 2: Label
    print("\n[3/4] Labeling regimes...")
    labeled = label_data(features)

    # Class distribution
    print("\n  Regime distribution:")
    for regime, name in REGIME_NAMES.items():
        count = (labeled["Regime"] == regime).sum()
        pct = 100 * count / len(labeled)
        print(f"    {name}: {count} ({pct:.1f}%)")

    # Balance if needed
    labeled_balanced = balance_classes(labeled, undersampling_ratio=0.3)

    # Step 3: Train
    print(f"\n[4/4] Training {model_type} classifier...")
    classifier = RegimeClassifier()
    results = classifier.train(labeled_balanced, model_type=model_type)

    # Report
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Test Accuracy: {results['test_accuracy']:.3f}")
    print(f"CV F1 Score:   {results['cv_f1_mean']:.3f} ± {results['cv_f1_std']:.3f}")
    print("\nClassification Report:")
    print(results["classification_report"])

    # Feature importance
    importance = classifier.get_feature_importance()
    if importance is not None:
        print("\nTop Feature Importance:")
        print(importance.head(5).to_string())

    # Save
    if save_results:
        labeled.to_csv(os.path.join(output_dir, f"{config_name}_labeled.csv"))
        if importance is not None:
            importance.to_csv(os.path.join(output_dir, f"{config_name}_importance.csv"))

    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Experiment B: Regime Classification")
    parser.add_argument("--config", default="extended", choices=["minimal", "extended", "full_crypto"])
    parser.add_argument("--model", default="random_forest", choices=["logistic", "random_forest"])

    args = parser.parse_args()
    run_experiment_b(config_name=args.config, model_type=args.model)
