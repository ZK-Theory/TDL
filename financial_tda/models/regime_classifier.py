"""
Regime classifier for financial market states.

This module provides tools for classifying market regimes (crisis vs normal)
using topological features extracted from sliding window analysis. It includes
labeling logic based on VIX and drawdown thresholds, feature preprocessing,
and ML classifiers with proper time-series cross-validation.

References:
    Gidea, M., & Katz, Y. (2018). Topological data analysis of financial
        time series: Landscapes of crashes. Physica A, 491, 820-834.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

logger = logging.getLogger(__name__)

# Type aliases
ClassifierType = Literal["random_forest", "svm", "xgboost", "gradient_boosting"]
RegimeLabel = Literal["crisis", "normal"]


def create_regime_labels(
    prices: pd.Series,
    vix: pd.Series,
    vix_crisis_threshold: float = 25.0,
    vix_crisis_days: int = 5,
    vix_normal_threshold: float = 20.0,
    vix_normal_days: int = 20,
    drawdown_threshold: float = 0.15,
    rolling_window: int = 252,
) -> pd.Series:
    """
    Create regime labels based on VIX levels and price drawdowns.

    Labels are assigned using two complementary criteria:
    1. VIX-based: Crisis when VIX > threshold for consecutive days
    2. Drawdown-based: Crisis when drawdown exceeds threshold from rolling peak

    Periods that don't clearly fall into either category are labeled as NaN
    (ambiguous) and excluded from training.

    Args:
        prices: Price series (e.g., S&P 500 index) with DatetimeIndex.
        vix: VIX index series aligned with prices (same DatetimeIndex).
        vix_crisis_threshold: VIX level above which market is in crisis. Default 25.
        vix_crisis_days: Minimum consecutive days VIX must exceed threshold. Default 5.
        vix_normal_threshold: VIX level below which market is normal. Default 20.
        vix_normal_days: Minimum consecutive days VIX must be below threshold. Default 20.
        drawdown_threshold: Maximum drawdown from peak indicating crisis. Default 0.15 (15%).
        rolling_window: Window size for computing rolling peak. Default 252 (1 year).

    Returns:
        Series with values 1 (crisis), 0 (normal), or NaN (ambiguous),
        indexed by date.

    Examples:
        >>> prices = pd.Series([100, 99, 85, 80, 95], index=pd.date_range('2020-01-01', periods=5))
        >>> vix = pd.Series([15, 20, 35, 40, 25], index=pd.date_range('2020-01-01', periods=5))
        >>> labels = create_regime_labels(prices, vix)
        >>> print(labels)

    Notes:
        - Crisis is labeled as 1, Normal as 0
        - Ambiguous periods (NaN) should be excluded from training
        - Labels are forward-looking; use care with train/test splits
    """
    # Ensure aligned indices
    prices = prices.copy()
    vix = vix.copy()

    # Align to common index
    common_index = prices.index.intersection(vix.index)
    if len(common_index) == 0:
        raise ValueError("prices and vix have no overlapping dates")

    prices = prices.loc[common_index]
    vix = vix.loc[common_index]

    # Initialize labels as NaN (ambiguous)
    labels = pd.Series(index=common_index, dtype=float)
    labels[:] = np.nan

    # --- VIX-based crisis detection ---
    # Identify periods where VIX > crisis threshold
    vix_high = (vix > vix_crisis_threshold).astype(int)

    # Find runs of consecutive high VIX days
    vix_crisis_runs = _consecutive_runs(vix_high, min_length=vix_crisis_days)
    for start_idx, end_idx in vix_crisis_runs:
        labels.iloc[start_idx : end_idx + 1] = 1  # Crisis

    # --- Drawdown-based crisis detection ---
    # Compute rolling peak
    rolling_peak = prices.rolling(window=rolling_window, min_periods=1).max()

    # Compute drawdown as percentage from peak
    drawdown = (rolling_peak - prices) / rolling_peak

    # Label crisis when drawdown exceeds threshold
    drawdown_crisis = drawdown > drawdown_threshold
    labels.loc[drawdown_crisis] = 1  # Crisis

    # --- VIX-based normal detection ---
    # Identify periods where VIX < normal threshold
    vix_low = (vix < vix_normal_threshold).astype(int)

    # Find runs of consecutive low VIX days
    vix_normal_runs = _consecutive_runs(vix_low, min_length=vix_normal_days)
    for start_idx, end_idx in vix_normal_runs:
        # Only label as normal if not already labeled as crisis
        for i in range(start_idx, end_idx + 1):
            if pd.isna(labels.iloc[i]):
                labels.iloc[i] = 0  # Normal

    logger.info(
        "Created regime labels: %d crisis, %d normal, %d ambiguous",
        (labels == 1).sum(),
        (labels == 0).sum(),
        labels.isna().sum(),
    )

    return labels


def _consecutive_runs(
    binary_series: pd.Series, min_length: int
) -> list[tuple[int, int]]:
    """
    Find runs of consecutive 1s in a binary series.

    Args:
        binary_series: Series of 0s and 1s.
        min_length: Minimum run length to include.

    Returns:
        List of (start_idx, end_idx) tuples for qualifying runs.
    """
    runs = []
    in_run = False
    run_start = 0

    for i, val in enumerate(binary_series):
        if val == 1 and not in_run:
            # Start of run
            in_run = True
            run_start = i
        elif val == 0 and in_run:
            # End of run
            run_length = i - run_start
            if run_length >= min_length:
                runs.append((run_start, i - 1))
            in_run = False

    # Check if run extends to end
    if in_run:
        run_length = len(binary_series) - run_start
        if run_length >= min_length:
            runs.append((run_start, len(binary_series) - 1))

    return runs


def prepare_features(
    windowed_features: pd.DataFrame,
    feature_columns: list[str] | None = None,
    scaler: StandardScaler | None = None,
    fit_scaler: bool = True,
) -> tuple[NDArray[np.floating], StandardScaler]:
    """
    Prepare windowed features for classification.

    Flattens window-level features into a 2D array suitable for ML classifiers,
    with optional standardization.

    Args:
        windowed_features: DataFrame from extract_windowed_features() with
            columns including 'window_start', 'window_end', and feature columns.
        feature_columns: List of column names to use as features. If None,
            uses all numeric columns except 'window_start' and 'window_end'.
        scaler: Pre-fitted StandardScaler for transform-only mode.
            If None, a new scaler is created.
        fit_scaler: Whether to fit the scaler on this data. Set False for
            inference on new data.

    Returns:
        Tuple of (feature_array, scaler) where:
            - feature_array: 2D array of shape (n_windows, n_features)
            - scaler: Fitted StandardScaler for consistent preprocessing

    Examples:
        >>> features_df = extract_windowed_features(returns)
        >>> X, scaler = prepare_features(features_df)
        >>> print(X.shape)  # (n_windows, n_features)

    Notes:
        - NaN values are replaced with 0 after logging a warning
        - Standardization (zero mean, unit variance) improves classifier performance
        - Save the scaler for consistent preprocessing during inference
    """
    df = windowed_features.copy()

    # Identify feature columns
    if feature_columns is None:
        exclude_cols = {"window_start", "window_end"}
        feature_columns = [
            col
            for col in df.columns
            if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col])
        ]

    if len(feature_columns) == 0:
        raise ValueError("No numeric feature columns found")

    # Extract feature matrix
    X = df[feature_columns].values.astype(np.float64)

    # Handle NaN values
    nan_count = np.isnan(X).sum()
    if nan_count > 0:
        logger.warning(
            "Found %d NaN values in features, replacing with 0",
            nan_count,
        )
        X = np.nan_to_num(X, nan=0.0)

    # Standardize features
    if scaler is None:
        scaler = StandardScaler()

    if fit_scaler:
        X = scaler.fit_transform(X)
    else:
        X = scaler.transform(X)

    logger.debug(
        "Prepared features: %d samples, %d features",
        X.shape[0],
        X.shape[1],
    )

    return X, scaler


class RegimeClassifier:
    """
    Classifier for financial market regimes using topological features.

    Supports multiple classifier types with time-series aware cross-validation
    to prevent future data leakage.

    Attributes:
        classifier_type: Type of classifier ('random_forest', 'svm', 'xgboost',
            'gradient_boosting').
        classifier: The underlying sklearn/xgboost classifier instance.
        scaler: StandardScaler for feature preprocessing.
        is_fitted: Whether the classifier has been fitted.

    Examples:
        >>> clf = RegimeClassifier(classifier_type='random_forest')
        >>> clf.fit(X_train, y_train, time_index)
        >>> predictions = clf.predict(X_test)
        >>> probabilities = clf.predict_proba(X_test)
    """

    def __init__(
        self,
        classifier_type: ClassifierType = "random_forest",
        class_weight: str | dict | None = "balanced",
        random_state: int = 42,
        **classifier_kwargs: Any,
    ) -> None:
        """
        Initialize the regime classifier.

        Args:
            classifier_type: Type of classifier to use. Options:
                - 'random_forest': Random Forest (default, good baseline)
                - 'svm': Support Vector Machine with RBF kernel
                - 'xgboost': XGBoost classifier (requires xgboost package)
                - 'gradient_boosting': Gradient Boosting classifier
            class_weight: Class weight strategy for imbalanced data.
                - 'balanced': Automatically adjust weights inversely proportional
                  to class frequencies (recommended for crisis detection)
                - dict: Manual weights like {0: 1, 1: 3}
                - None: No weighting
            random_state: Random seed for reproducibility.
            **classifier_kwargs: Additional keyword arguments passed to the
                underlying classifier constructor.

        Raises:
            ValueError: If classifier_type is not recognized.
        """
        self.classifier_type = classifier_type
        self.class_weight = class_weight
        self.random_state = random_state
        self.classifier_kwargs = classifier_kwargs

        self.classifier = self._create_classifier()
        self.scaler: StandardScaler | None = None
        self.is_fitted: bool = False

    def _create_classifier(self) -> Any:
        """Create the underlying classifier instance."""
        if self.classifier_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=100,
                class_weight=self.class_weight,
                random_state=self.random_state,
                n_jobs=-1,
                **self.classifier_kwargs,
            )
        elif self.classifier_type == "svm":
            # SVM doesn't support class_weight='balanced' directly for predict_proba
            # Use probability=True for probability estimates
            return SVC(
                kernel="rbf",
                class_weight=self.class_weight,
                random_state=self.random_state,
                probability=True,
                **self.classifier_kwargs,
            )
        elif self.classifier_type == "xgboost":
            try:
                from xgboost import XGBClassifier
            except ImportError as e:
                raise ImportError(
                    "xgboost package required for XGBoost classifier. "
                    "Install with: pip install xgboost"
                ) from e

            # XGBoost uses scale_pos_weight for imbalanced data
            return XGBClassifier(
                n_estimators=100,
                random_state=self.random_state,
                eval_metric="logloss",
                **self.classifier_kwargs,
            )
        elif self.classifier_type == "gradient_boosting":
            # GradientBoostingClassifier doesn't support class_weight
            # Handle imbalance via sample_weight in fit()
            return GradientBoostingClassifier(
                n_estimators=100,
                random_state=self.random_state,
                **self.classifier_kwargs,
            )
        else:
            raise ValueError(
                f"Unknown classifier_type '{self.classifier_type}'. "
                f"Must be one of: random_forest, svm, xgboost, gradient_boosting"
            )

    def fit(
        self,
        X: NDArray[np.floating],
        y: NDArray[np.integer],
        time_index: pd.DatetimeIndex | None = None,
        sample_weight: NDArray[np.floating] | None = None,
    ) -> "RegimeClassifier":
        """
        Fit the classifier on training data.

        Args:
            X: Feature array of shape (n_samples, n_features).
            y: Label array of shape (n_samples,) with values 0 (normal) or 1 (crisis).
            time_index: DatetimeIndex for temporal ordering. Used for logging
                and optional time-based validations.
            sample_weight: Optional sample weights for handling imbalanced data.
                Particularly useful for gradient_boosting which doesn't support
                class_weight.

        Returns:
            Self for method chaining.

        Notes:
            For time-series data, use time-aware train/test splitting before
            calling fit() to prevent future data leakage.
        """
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)

        if X.shape[0] != len(y):
            raise ValueError(
                f"X and y must have same number of samples: {X.shape[0]} vs {len(y)}"
            )

        # Log class distribution
        n_crisis = (y == 1).sum()
        n_normal = (y == 0).sum()
        logger.info(
            "Fitting %s classifier: %d normal, %d crisis samples (%.1f%% crisis)",
            self.classifier_type,
            n_normal,
            n_crisis,
            100 * n_crisis / len(y) if len(y) > 0 else 0,
        )

        # Compute sample weights for imbalanced classes if not provided
        if (
            sample_weight is None
            and self.classifier_type == "gradient_boosting"
            and self.class_weight == "balanced"
        ):
            # Compute balanced sample weights
            class_counts = np.bincount(y)
            total = len(y)
            sample_weight = np.array(
                [total / (2 * class_counts[label]) for label in y]
            )

        # Fit classifier
        if sample_weight is not None:
            self.classifier.fit(X, y, sample_weight=sample_weight)
        else:
            self.classifier.fit(X, y)

        self.is_fitted = True

        if time_index is not None:
            logger.info(
                "Training period: %s to %s",
                time_index.min().strftime("%Y-%m-%d"),
                time_index.max().strftime("%Y-%m-%d"),
            )

        return self

    def predict(self, X: NDArray[np.floating]) -> NDArray[np.integer]:
        """
        Predict regime labels for new data.

        Args:
            X: Feature array of shape (n_samples, n_features).

        Returns:
            Predicted labels of shape (n_samples,) with values 0 or 1.

        Raises:
            RuntimeError: If classifier has not been fitted.
        """
        if not self.is_fitted:
            raise RuntimeError("Classifier must be fitted before prediction")

        X = np.asarray(X, dtype=np.float64)
        return self.classifier.predict(X)

    def predict_proba(self, X: NDArray[np.floating]) -> NDArray[np.floating]:
        """
        Predict class probabilities for new data.

        Args:
            X: Feature array of shape (n_samples, n_features).

        Returns:
            Probability array of shape (n_samples, 2) where columns are
            [P(normal), P(crisis)].

        Raises:
            RuntimeError: If classifier has not been fitted.
        """
        if not self.is_fitted:
            raise RuntimeError("Classifier must be fitted before prediction")

        X = np.asarray(X, dtype=np.float64)
        return self.classifier.predict_proba(X)

    def cross_validate(
        self,
        X: NDArray[np.floating],
        y: NDArray[np.integer],
        time_index: pd.DatetimeIndex,
        n_splits: int = 5,
    ) -> dict[str, Any]:
        """
        Perform time-series cross-validation.

        Uses sklearn's TimeSeriesSplit to ensure no future data leakage.
        Each fold uses all previous data for training and the next
        sequential block for testing.

        Args:
            X: Feature array of shape (n_samples, n_features).
            y: Label array of shape (n_samples,).
            time_index: DatetimeIndex for temporal ordering.
            n_splits: Number of CV folds. Default 5.

        Returns:
            Dictionary with:
                - 'precision': List of precision scores per fold
                - 'recall': List of recall scores per fold
                - 'f1': List of F1 scores per fold
                - 'mean_precision': Mean precision across folds
                - 'mean_recall': Mean recall across folds
                - 'mean_f1': Mean F1 across folds
                - 'fold_details': List of dicts with fold-specific info

        Notes:
            - TimeSeriesSplit ensures training data always precedes test data
            - First fold may have less training data
            - All metrics computed for crisis class (label=1)
        """
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)

        tscv = TimeSeriesSplit(n_splits=n_splits)

        precision_scores = []
        recall_scores = []
        f1_scores = []
        fold_details = []

        for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X)):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            # Create a fresh classifier instance for each fold
            fold_clf = RegimeClassifier(
                classifier_type=self.classifier_type,
                class_weight=self.class_weight,
                random_state=self.random_state,
                **self.classifier_kwargs,
            )

            # Fit and predict
            fold_clf.fit(X_train, y_train)
            y_pred = fold_clf.predict(X_test)

            # Compute metrics for crisis class (label=1)
            precision = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
            recall = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
            f1 = f1_score(y_test, y_pred, pos_label=1, zero_division=0)

            precision_scores.append(precision)
            recall_scores.append(recall)
            f1_scores.append(f1)

            # Store fold details
            fold_info = {
                "fold": fold_idx + 1,
                "train_size": len(train_idx),
                "test_size": len(test_idx),
                "train_crisis_pct": 100 * (y_train == 1).sum() / len(y_train),
                "test_crisis_pct": 100 * (y_test == 1).sum() / len(y_test),
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "train_start": time_index[train_idx[0]].strftime("%Y-%m-%d"),
                "train_end": time_index[train_idx[-1]].strftime("%Y-%m-%d"),
                "test_start": time_index[test_idx[0]].strftime("%Y-%m-%d"),
                "test_end": time_index[test_idx[-1]].strftime("%Y-%m-%d"),
            }
            fold_details.append(fold_info)

            logger.info(
                "Fold %d: P=%.3f, R=%.3f, F1=%.3f (train: %s to %s, test: %s to %s)",
                fold_idx + 1,
                precision,
                recall,
                f1,
                fold_info["train_start"],
                fold_info["train_end"],
                fold_info["test_start"],
                fold_info["test_end"],
            )

        return {
            "precision": precision_scores,
            "recall": recall_scores,
            "f1": f1_scores,
            "mean_precision": float(np.mean(precision_scores)),
            "mean_recall": float(np.mean(recall_scores)),
            "mean_f1": float(np.mean(f1_scores)),
            "fold_details": fold_details,
        }


def evaluate_classifier(
    y_true: NDArray[np.integer],
    y_pred: NDArray[np.integer],
    y_proba: NDArray[np.floating] | None = None,
) -> dict[str, Any]:
    """
    Evaluate classifier performance with comprehensive metrics.

    Args:
        y_true: Ground truth labels of shape (n_samples,).
        y_pred: Predicted labels of shape (n_samples,).
        y_proba: Predicted probabilities of shape (n_samples, 2) or (n_samples,).
            If 2D, uses column 1 (crisis probability). Optional.

    Returns:
        Dictionary with:
            - 'precision': Precision for crisis class
            - 'recall': Recall for crisis class
            - 'f1': F1 score for crisis class
            - 'f1_weighted': Weighted F1 across all classes
            - 'roc_auc': ROC-AUC score (if y_proba provided)
            - 'pr_auc': Precision-Recall AUC (if y_proba provided)
            - 'confusion_matrix': 2x2 confusion matrix
            - 'classification_report': Full classification report string

    Examples:
        >>> y_true = np.array([0, 0, 1, 1, 0])
        >>> y_pred = np.array([0, 1, 1, 0, 0])
        >>> y_proba = np.array([[0.8, 0.2], [0.3, 0.7], [0.2, 0.8], [0.6, 0.4], [0.9, 0.1]])
        >>> metrics = evaluate_classifier(y_true, y_pred, y_proba)
        >>> print(f"F1: {metrics['f1']:.3f}")
    """
    y_true = np.asarray(y_true, dtype=np.int64)
    y_pred = np.asarray(y_pred, dtype=np.int64)

    # Basic metrics for crisis class
    precision = precision_score(y_true, y_pred, pos_label=1, zero_division=0)
    recall = recall_score(y_true, y_pred, pos_label=1, zero_division=0)
    f1 = f1_score(y_true, y_pred, pos_label=1, zero_division=0)
    f1_weighted = f1_score(y_true, y_pred, average="weighted", zero_division=0)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    # Classification report
    report = classification_report(
        y_true,
        y_pred,
        target_names=["normal", "crisis"],
        zero_division=0,
    )

    result = {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "f1_weighted": float(f1_weighted),
        "confusion_matrix": cm,
        "classification_report": report,
    }

    # Probability-based metrics
    if y_proba is not None:
        y_proba = np.asarray(y_proba, dtype=np.float64)

        # Extract crisis probability
        if y_proba.ndim == 2:
            crisis_proba = y_proba[:, 1]
        else:
            crisis_proba = y_proba

        # ROC-AUC
        try:
            roc_auc = roc_auc_score(y_true, crisis_proba)
            result["roc_auc"] = float(roc_auc)
        except ValueError as e:
            logger.warning("Could not compute ROC-AUC: %s", e)
            result["roc_auc"] = np.nan

        # Precision-Recall AUC
        try:
            pr_precision, pr_recall, _ = precision_recall_curve(y_true, crisis_proba)
            # Compute AUC using trapezoidal rule
            # Handle numpy version differences (trapezoid in 2.0+, trapz in older)
            if hasattr(np, "trapezoid"):
                pr_auc = -np.trapezoid(pr_precision, pr_recall)
            else:
                pr_auc = -np.trapz(pr_precision, pr_recall)
            result["pr_auc"] = float(pr_auc)
        except ValueError as e:
            logger.warning("Could not compute PR-AUC: %s", e)
            result["pr_auc"] = np.nan

    logger.info(
        "Evaluation: P=%.3f, R=%.3f, F1=%.3f, F1_weighted=%.3f",
        precision,
        recall,
        f1,
        f1_weighted,
    )

    return result


def save_model(
    classifier: RegimeClassifier,
    path: str | Path,
    scaler: StandardScaler | None = None,
) -> None:
    """
    Save trained classifier to disk using joblib.

    Args:
        classifier: Fitted RegimeClassifier instance.
        path: File path for saving. Will add '.joblib' extension if not present.
        scaler: Optional StandardScaler to save alongside classifier.

    Examples:
        >>> clf = RegimeClassifier()
        >>> clf.fit(X_train, y_train)
        >>> save_model(clf, 'models/regime_clf.joblib', scaler=scaler)
    """
    path = Path(path)
    if path.suffix != ".joblib":
        path = path.with_suffix(".joblib")

    # Create directory if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    # Save model and scaler together
    model_data = {
        "classifier": classifier,
        "scaler": scaler,
        "classifier_type": classifier.classifier_type,
        "is_fitted": classifier.is_fitted,
    }

    joblib.dump(model_data, path)
    logger.info("Saved model to %s", path)


def load_model(path: str | Path) -> tuple[RegimeClassifier, StandardScaler | None]:
    """
    Load trained classifier from disk.

    Args:
        path: File path to load from.

    Returns:
        Tuple of (RegimeClassifier, StandardScaler or None).

    Raises:
        FileNotFoundError: If path doesn't exist.

    Examples:
        >>> clf, scaler = load_model('models/regime_clf.joblib')
        >>> predictions = clf.predict(X_test)
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")

    model_data = joblib.load(path)

    classifier = model_data["classifier"]
    scaler = model_data.get("scaler")

    logger.info(
        "Loaded %s classifier (fitted=%s) from %s",
        model_data.get("classifier_type", "unknown"),
        model_data.get("is_fitted", "unknown"),
        path,
    )

    return classifier, scaler
